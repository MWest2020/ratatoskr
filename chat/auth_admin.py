# SPDX-License-Identifier: EUPL-1.2
"""Routes achter de sessie: uitnodigen, en je eigen tweede factor.

Uitnodigen mag alleen de eigenaar. Zelf-registratie bestaat niet: één
installatie is één team, en de grens is de installatie.
"""
import auth
import auth_store as store
from auth_routes import _json


def _person(session):
    return store.person(session["persoon"])


def invite(h, session):
    """Maak een eenmalige, verlopende uitnodiging. Alleen de eigenaar."""
    if not _person(session)["eigenaar"]:
        return _json(h, 403, {"error": "alleen de eigenaar kan uitnodigen"})
    token = auth.new_invite("uitnodiging")
    return _json(h, 201, {
        "pad": "/login?uitnodiging=" + token,
        "verloopt_over_dagen": auth.INVITE_TTL // 86400,
    })


def revoke_invites(h, session):
    if not _person(session)["eigenaar"]:
        return _json(h, 403, {"error": "alleen de eigenaar kan uitnodigingen intrekken"})
    store.revoke_invites("uitnodiging")
    return _json(h, 200, {"status": "ingetrokken"})


def change_password(h, session, body):
    """Je eigen wachtwoord. Het huidige moet mee: anders is een geleende
    sessie genoeg om iemand permanent buiten te sluiten.

    Alle sessies gaan eruit, ook deze — en er komt meteen een nieuwe voor dit
    apparaat terug. Wie het oude wachtwoord had, is dus overal weg, en jij hoeft
    niet opnieuw in te loggen."""
    p = _person(session)
    current = body.get("huidig") or ""
    new = body.get("nieuw") or ""
    if not auth.password_matches(current, p["hash"]):
        return _json(h, 403, {"error": "het huidige wachtwoord klopt niet"})
    if len(new) < 12:
        return _json(h, 400, {"error": "nieuw wachtwoord minstens 12 tekens"})
    store.set_hash(p["id"], auth.hash_password(new))
    store.revoke_all_sessions(p["id"])
    token, csrf = auth.start_session(p["id"])
    return _json(h, 200, {"status": "gewijzigd", "csrf": csrf},
                 [("Set-Cookie", auth.cookie_header(token, h.headers.get("Host", "")))])


def totp_start(h, session):
    """Geef een geheim terug; het gaat pas aan als er een kloppende code komt.
    Anders sluit een verkeerd overgetypt geheim je uit je eigen account."""
    secret = auth.new_totp_secret()
    name = _person(session)["naam"]
    return _json(h, 200, {
        "geheim": secret,
        "otpauth": "otpauth://totp/boomhuis:{}?secret={}&issuer=boomhuis".format(
            name, secret),
    })


def totp_confirm(h, session, body):
    secret = (body.get("geheim") or "").strip()
    ok, counter = auth.totp_matches(secret, body.get("code") or "") if secret else (False, None)
    if not ok:
        return _json(h, 400, {"error": "code klopt niet"})
    store.set_totp(session["persoon"], secret)
    store.set_totp_counter(session["persoon"], counter)
    return _json(h, 200, {"totp": True})


def totp_off(h, session):
    store.set_totp(session["persoon"], None)
    return _json(h, 200, {"totp": False})


def route(h, path, session, body=None):
    """True wanneer dit pad hier hoort en is afgehandeld."""
    if body is None:
        return False
    if path == "/api/uitnodiging":
        return invite(h, session)
    if path == "/api/uitnodiging/intrekken":
        return revoke_invites(h, session)
    if path == "/api/wachtwoord":
        return change_password(h, session, body)
    if path == "/api/totp/start":
        return totp_start(h, session)
    if path == "/api/totp/aan":
        return totp_confirm(h, session, body)
    if path == "/api/totp/uit":
        return totp_off(h, session)
    return False
