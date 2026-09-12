# SPDX-License-Identifier: EUPL-1.2
"""Routes behind the session: inviting, and your own second factor.

Only the owner may invite. Self-registration does not exist: one installation is
one team, and the installation is the boundary.
"""
import auth
import auth_store as store
from auth_routes import _json


def _person(session):
    return store.person(session["persoon"])


def invite(h, session):
    """Create a single-use, expiring invitation. Owner only."""
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
    """Your own password. The current one must come along: otherwise a borrowed
    session is enough to lock someone out permanently.

    All sessions are revoked, this one included — and a fresh one for this device
    comes straight back. Whoever had the old password is gone everywhere, and you
    do not have to log in again."""
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
    """Return a secret; it only turns on once a matching code arrives. Otherwise
    a mistyped secret locks you out of your own account."""
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
    """True when this path belongs here and has been handled."""
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
