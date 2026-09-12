# SPDX-License-Identifier: EUPL-1.2
"""The HTTP side of logging in: routes that need no session, plus the gate.

`server.py` stays thin: it calls `open_route()` for the paths allowed without a
session, and `gate()` for everything else under /api/.

Answers are deliberately stingy. An unknown name and a wrong password give the
same thing: "inloggen mislukt". Whoever wants to know whether a name exists does
not find out here.

The paths and the JSON field names stay Dutch: that is the contract with the PWA
that is already installed. See ADR-0001; that conversion is a change of its own.
"""
import json
import os

import auth
import auth_store as store
import auth_throttle as throttle
import settings

FAILED = {"error": "inloggen mislukt"}

# Paths that must work without a session — otherwise you can never log in.
OPEN = ("/api/login", "/api/setup", "/api/uitnodiging/gebruik", "/api/status")


def _source(h):
    """The address this request comes from, for the throttle. Behind a reverse
    proxy that is the proxy, so X-Forwarded-For takes precedence."""
    forwarded = (h.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or h.client_address[0]


def _json(h, code, payload, extra=None):
    data = json.dumps(payload).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(data)))
    h.send_header("Cache-Control", "no-store")
    for k, v in (extra or []):
        h.send_header(k, v)
    h.end_headers()
    h.wfile.write(data)
    return True


def status(h):
    """What the login page needs to know before anyone exists: is this a fresh
    installation, and will this person demand a second factor?"""
    return _json(h, 200, {"personen": store.person_count()})


def session_info(h):
    s = auth.session_from_cookie(h.headers)
    if s is None:
        return _json(h, 401, {"error": "geen sessie"})
    p = store.person(s["persoon"])
    return _json(h, 200, {"naam": p["naam"], "eigenaar": bool(p["eigenaar"]),
                          "csrf": s["csrf"], "totp": bool(p["totp"])})


def log_in(h, body):
    name = (body.get("naam") or "").strip()
    password = body.get("wachtwoord") or ""
    keys = ["naam:" + name.lower(), "bron:" + _source(h)]
    wait = max(throttle.blocked_for(k) for k in keys)
    if wait:
        return _json(h, 429, {"error": "te veel pogingen", "wacht": wait})

    p = store.person_by_name(name) if name else None
    # Compute a hash for an unknown name too: otherwise the response time gives
    # away whether the account exists.
    stored = p["hash"] if p else auth.hash_password("x", n=2 ** 14)
    good = auth.password_matches(password, stored) and p is not None

    if not good:
        for k in keys:
            throttle.note_failure(k)
        return _json(h, 401, FAILED)

    if p["totp"]:
        code = (body.get("code") or "").strip()
        if not code:
            # Name and password were right; the app asking for a code now leaks
            # nothing extra. Do not count a failure: that would make every login
            # with a second factor engage the brake.
            return _json(h, 401, {"error": "code nodig", "totp": True})
        ok, counter = auth.totp_matches(p["totp"], code, last=p["totp_laatste"])
        if not ok:
            for k in keys:
                throttle.note_failure(k)
            return _json(h, 401, {"error": "inloggen mislukt", "totp": True})
        store.set_totp_counter(p["id"], counter)

    for k in keys:
        throttle.clear_attempts(k)
    if auth.outdated(p["hash"]):
        store.set_hash(p["id"], auth.hash_password(password))
    token, csrf = auth.start_session(p["id"])
    return _json(h, 200, {"naam": p["naam"], "csrf": csrf},
                 [("Set-Cookie", auth.cookie_header(token, h.headers.get("Host", "")))])


def log_out(h, body):
    auth.stop_session(h.headers, everywhere=bool(body.get("overal")))
    return _json(h, 200, {"status": "uitgelogd"},
                 [("Set-Cookie", auth.cookie_header("", h.headers.get("Host", ""),
                                                    delete=True))])


def _create_account(h, name, password, owner):
    name = (name or "").strip()
    if len(name) < 2 or len(password or "") < 12:
        return _json(h, 400, {"error": "naam minstens 2 tekens, wachtwoord minstens 12"})
    pid = store.create_person(name, auth.hash_password(password), owner)
    if pid is None:
        return _json(h, 409, {"error": "die naam bestaat al"})
    token, csrf = auth.start_session(pid)
    return _json(h, 201, {"naam": name, "csrf": csrf},
                 [("Set-Cookie", auth.cookie_header(token, h.headers.get("Host", "")))])


def setup(h, body):
    """The first person. Only as long as there is nobody."""
    if store.person_count() > 0:
        return _json(h, 403, {"error": "er is al een account"})
    token = body.get("token") or ""
    # Two keys fit: the printed setup link, and once the old shared write token
    # of an existing installation.
    if not (auth.invite_valid(token, "setup") or auth.setup_token_valid(token)):
        throttle.note_failure("bron:" + _source(h))
        return _json(h, 403, {"error": "ongeldige of verlopen setup-link"})
    answer = _create_account(h, body.get("naam"), body.get("wachtwoord"), owner=True)
    auth.use_invite(token)               # single-use, also for the old token
    store.revoke_invites("setup")
    return answer


def use_invite(h, body):
    token = body.get("token") or ""
    if not auth.invite_valid(token, "uitnodiging"):
        throttle.note_failure("bron:" + _source(h))
        return _json(h, 403, {"error": "ongeldige of verlopen uitnodiging"})
    if not auth.use_invite(token):        # mark first: single-use, even in a race
        return _json(h, 403, {"error": "ongeldige of verlopen uitnodiging"})
    return _create_account(h, body.get("naam"), body.get("wachtwoord"), owner=False)


def open_route(h, path, body=None):
    """Routes allowed without a session. True = handled."""
    if path == "/api/status":
        return status(h)
    if path == "/api/login" and body is not None:
        return log_in(h, body)
    if path == "/api/setup" and body is not None:
        return setup(h, body)
    if path == "/api/uitnodiging/gebruik" and body is not None:
        return use_invite(h, body)
    return False


def gate(h, path, writes):
    """The session check. Returns the session row, or None when an answer has
    already been sent."""
    s = auth.session_from_cookie(h.headers)
    if s is None:
        _json(h, 401, {"error": "inloggen vereist"})
        return None
    if writes and not auth.csrf_matches(h.headers, s):
        _json(h, 403, {"error": "ontbrekend of ongeldig sessietoken"})
        return None
    return s


def print_setup_link_at_start():
    """On a fresh installation: print a one-time setup link.

    No default password — that is the thing every self-hosted product breaks on.
    If an old shared write token exists, we say that it works once too.
    """
    if store.person_count() > 0:
        return
    store.revoke_invites("setup")
    token = auth.new_invite("setup")
    base = settings.read("URL").rstrip("/")
    print("[chat] nog geen account. Maak de eigenaar aan via:", flush=True)
    print("[chat]   {}/login?setup={}".format(base or "<jouw boomhuis-url>", token),
          flush=True)
    if settings.read("APP_TOKEN").strip():
        print("[chat]   (of eenmalig met het oude APP_TOKEN)", flush=True)
