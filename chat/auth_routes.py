# SPDX-License-Identifier: EUPL-1.2
"""De HTTP-kant van inloggen: routes die géén sessie vereisen, plus de gate.

`server.py` blijft dun: het roept `open_route()` voor de paden die zonder
sessie mogen, en `gate()` voor al het andere onder /api/.

Antwoorden zijn opzettelijk karig. Een onbekende naam en een fout wachtwoord
geven hetzelfde: "inloggen mislukt". Wie wil weten of een naam bestaat, komt er
hier niet achter.

De paden en de veldnamen in de JSON blijven Nederlands: dat is het contract met
de al geïnstalleerde PWA. Zie ADR-0001; die omzetting is een aparte change.
"""
import json
import os

import auth
import auth_store as store
import auth_throttle as throttle
import settings

FAILED = {"error": "inloggen mislukt"}

# Paden die zonder sessie moeten kunnen — anders kun je nooit inloggen.
OPEN = ("/api/login", "/api/setup", "/api/uitnodiging/gebruik", "/api/status")


def _source(h):
    """Het adres waar dit verzoek vandaan komt, voor de rem. Achter een reverse
    proxy is dat de proxy, dus X-Forwarded-For gaat voor."""
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
    """Wat de inlogpagina moet weten vóór er iemand is: is dit een verse
    installatie, en eist deze persoon straks een tweede factor?"""
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
    # Ook bij een onbekende naam een hash uitrekenen: anders verraadt de
    # antwoordtijd of het account bestaat.
    stored = p["hash"] if p else auth.hash_password("x", n=2 ** 14)
    good = auth.password_matches(password, stored) and p is not None

    if not good:
        for k in keys:
            throttle.note_failure(k)
        return _json(h, 401, FAILED)

    if p["totp"]:
        code = (body.get("code") or "").strip()
        if not code:
            # Naam en wachtwoord klopten; dat de app nu om een code vraagt lekt
            # niets extra's. Geen mislukking tellen: dan zou elke login met
            # tweede factor de rem aanzetten.
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
    """De eerste persoon. Alleen zolang er niemand is."""
    if store.person_count() > 0:
        return _json(h, 403, {"error": "er is al een account"})
    token = body.get("token") or ""
    # Twee sleutels passen: de afgedrukte setup-link, en éénmalig het oude
    # gedeelde schrijf-token van een bestaande installatie.
    if not (auth.invite_valid(token, "setup") or auth.setup_token_valid(token)):
        throttle.note_failure("bron:" + _source(h))
        return _json(h, 403, {"error": "ongeldige of verlopen setup-link"})
    answer = _create_account(h, body.get("naam"), body.get("wachtwoord"), owner=True)
    auth.use_invite(token)               # eenmalig, ook als het het oude token was
    store.revoke_invites("setup")
    return answer


def use_invite(h, body):
    token = body.get("token") or ""
    if not auth.invite_valid(token, "uitnodiging"):
        throttle.note_failure("bron:" + _source(h))
        return _json(h, 403, {"error": "ongeldige of verlopen uitnodiging"})
    if not auth.use_invite(token):        # markeer eerst: eenmalig, ook bij een race
        return _json(h, 403, {"error": "ongeldige of verlopen uitnodiging"})
    return _create_account(h, body.get("naam"), body.get("wachtwoord"), owner=False)


def open_route(h, path, body=None):
    """Routes die zonder sessie mogen. True = afgehandeld."""
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
    """De sessiecontrole. Geeft de sessierij terug, of None als er al een
    antwoord verstuurd is."""
    s = auth.session_from_cookie(h.headers)
    if s is None:
        _json(h, 401, {"error": "inloggen vereist"})
        return None
    if writes and not auth.csrf_matches(h.headers, s):
        _json(h, 403, {"error": "ontbrekend of ongeldig sessietoken"})
        return None
    return s


def print_setup_link_at_start():
    """Bij een verse installatie: druk een eenmalige setup-link af.

    Geen standaardwachtwoord — dat is het ding waar elk zelfgehost product op
    stukloopt. Bestaat er al een oud gedeeld schrijf-token, dan zeggen we dat
    dat éénmalig ook werkt.
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
