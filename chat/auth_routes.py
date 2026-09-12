# SPDX-License-Identifier: EUPL-1.2
"""The HTTP side of logging in: routes that need no session, plus the gate.

`server.py` stays thin: it calls `open_route()` for the paths allowed without a
session, and `gate()` for everything else under /api/. Answers are
deliberately stingy — an unknown name and a wrong password both give
"sign-in failed" — and the paths and JSON field names stay Dutch: that is the
contract with the already-installed PWA. See ADR-0001; that conversion is a
change of its own.
"""
import json
import os

import auth
import auth_factors
import auth_hashguard as hashguard
import auth_store as store
import auth_throttle as throttle
import settings

FAILED = {"error": "sign-in failed"}

# Paths that must work without a session — otherwise you can never log in.
OPEN = ("/api/login", "/api/setup", "/api/uitnodiging/gebruik", "/api/status")

# Fixed at import: a fresh dummy per request would itself cost a second
# scrypt call, making unknown names slower rather than equal (see log_in()).
_DUMMY_HASH = auth_factors.hash_password("geen-account-met-deze-naam")


def _source(h):
    """The request's source, for the throttle. Trust X-Forwarded-For only
    from a loopback peer (proxy on the same machine), then its LAST element —
    an appending proxy leaves the client's own, spoofable value up front."""
    peer = h.client_address[0]
    if peer not in ("127.0.0.1", "::1"):
        return peer
    return (h.headers.get("X-Forwarded-For") or "").split(",")[-1].strip() or peer


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
    """What the login page needs to know before anyone exists: is this fresh?"""
    return _json(h, 200, {"personen": store.person_count()})


def session_info(h):
    s = auth.session_from_cookie(h.headers)
    if s is None:
        return _json(h, 401, {"error": "no session"})
    p = store.person(s["persoon"])
    return _json(h, 200, {"naam": p["naam"], "eigenaar": bool(p["eigenaar"]),
                          "csrf": s["csrf"], "totp": bool(p["totp"])})


def log_in(h, body):
    name = (body.get("naam") or "").strip()
    password = body.get("wachtwoord") or ""
    keys = ["naam:" + name.lower(), "bron:" + _source(h)]
    wait = max(throttle.blocked_for(k) for k in keys)
    if wait:
        return _json(h, 429, {"error": "too many attempts", "wacht": wait})

    p = store.person_by_name(name) if name else None
    stored = p["hash"] if p else _DUMMY_HASH
    matched = hashguard.guarded(auth_factors.password_matches, password, stored)
    if matched is None:
        return _json(h, 429, {"error": "too busy, try again"})
    good = matched and p is not None

    if not good:
        for k in keys:
            throttle.note_failure(k)
        return _json(h, 401, FAILED)

    if p["totp"]:
        code = (body.get("code") or "").strip()
        if not code:
            # Name and password were right, so this leaks nothing extra. Do not
            # count a failure: that would brake every login with a second factor.
            return _json(h, 401, {"error": "code required", "totp": True})
        ok, counter = auth_factors.totp_matches(p["totp"], code, last=p["totp_laatste"])
        if not ok:
            for k in keys:
                throttle.note_failure(k)
            return _json(h, 401, {"error": "sign-in failed", "totp": True})
        store.set_totp_counter(p["id"], counter)

    for k in keys:
        throttle.clear_attempts(k)
    if auth_factors.outdated(p["hash"]):
        store.set_hash(p["id"], auth_factors.hash_password(password))
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
        return _json(h, 400, {"error": "name at least 2 characters, password at least 12"})
    hashed = hashguard.guarded(auth_factors.hash_password, password)
    if hashed is None:
        return _json(h, 429, {"error": "too busy, try again"})
    pid = store.create_person(name, hashed, owner)
    if pid is None:
        return _json(h, 409, {"error": "that name already exists"})
    token, csrf = auth.start_session(pid)
    return _json(h, 201, {"naam": name, "csrf": csrf},
                 [("Set-Cookie", auth.cookie_header(token, h.headers.get("Host", "")))])


def setup(h, body):
    """The first person. Only as long as there is nobody."""
    if store.person_count() > 0:
        return _json(h, 403, {"error": "there is already an account"})
    token = body.get("token") or ""
    # Two keys fit: the printed setup link, or once the old shared write token.
    via_invite = auth.invite_valid(token, "setup")
    if not (via_invite or auth.setup_token_valid(token)):
        throttle.note_failure("bron:" + _source(h))
        return _json(h, 403, {"error": "invalid or expired setup link"})
    # Mark first, like use_invite() below; the legacy token has no invite row
    # to mark, so the unique index on personen.eigenaar covers that branch.
    if via_invite and not auth.use_invite(token):
        return _json(h, 403, {"error": "invalid or expired setup link"})
    answer = _create_account(h, body.get("naam"), body.get("wachtwoord"), owner=True)
    store.revoke_invites("setup")
    return answer


def use_invite(h, body):
    token = body.get("token") or ""
    if not auth.invite_valid(token, "uitnodiging"):
        throttle.note_failure("bron:" + _source(h))
        return _json(h, 403, {"error": "invalid or expired invitation"})
    if not auth.use_invite(token):        # mark first: single-use, even in a race
        return _json(h, 403, {"error": "invalid or expired invitation"})
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
    """The session check. Returns the session row, or None when already answered."""
    s = auth.session_from_cookie(h.headers)
    if s is None:
        _json(h, 401, {"error": "sign-in required"})
        return None
    if writes and not auth.csrf_matches(h.headers, s):
        _json(h, 403, {"error": "missing or invalid session token"})
        return None
    return s


def print_setup_link_at_start():
    """On a fresh installation: print a one-time setup link. No default
    password — that is the thing every self-hosted product breaks on. If an
    old shared write token exists, we say that it works once too."""
    if store.person_count() > 0:
        return
    store.revoke_invites("setup")
    token = auth.new_invite("setup")
    base = settings.read("URL").rstrip("/")
    print("[chat] no account yet. Create the owner through:", flush=True)
    print("[chat]   {}/login?setup={}".format(base or "<your boomhuis url>", token),
          flush=True)
    if settings.read("APP_TOKEN").strip():
        print("[chat]   (or once with the old APP_TOKEN)", flush=True)
