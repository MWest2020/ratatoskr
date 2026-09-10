# SPDX-License-Identifier: EUPL-1.2
"""Routes achter de sessie: uitnodigen, en je eigen tweede factor.

Uitnodigen mag alleen de eigenaar. Zelf-registratie bestaat niet: één
installatie is één team, en de grens is de installatie.
"""
import auth
import auth_store as store
from auth_routes import _json


def _persoon(sessie):
    return store.persoon(sessie["persoon"])


def uitnodigen(h, sessie):
    """Maak een eenmalige, verlopende uitnodiging. Alleen de eigenaar."""
    if not _persoon(sessie)["eigenaar"]:
        return _json(h, 403, {"error": "alleen de eigenaar kan uitnodigen"})
    token = auth.nieuwe_uitnodiging("uitnodiging")
    return _json(h, 201, {
        "pad": "/login?uitnodiging=" + token,
        "verloopt_over_dagen": auth.UITNODIGING_DUUR // 86400,
    })


def uitnodigingen_intrekken(h, sessie):
    if not _persoon(sessie)["eigenaar"]:
        return _json(h, 403, {"error": "alleen de eigenaar kan uitnodigingen intrekken"})
    store.trek_uitnodigingen_in("uitnodiging")
    return _json(h, 200, {"status": "ingetrokken"})


def totp_starten(h, sessie):
    """Geef een geheim terug; het gaat pas aan als er een kloppende code komt.
    Anders sluit een verkeerd overgetypt geheim je uit je eigen account."""
    geheim = auth.nieuw_totp_geheim()
    naam = _persoon(sessie)["naam"]
    return _json(h, 200, {
        "geheim": geheim,
        "otpauth": "otpauth://totp/boomhuis:{}?secret={}&issuer=boomhuis".format(
            naam, geheim),
    })


def totp_bevestigen(h, sessie, body):
    geheim = (body.get("geheim") or "").strip()
    ok, teller = auth.totp_klopt(geheim, body.get("code") or "") if geheim else (False, None)
    if not ok:
        return _json(h, 400, {"error": "code klopt niet"})
    store.zet_totp(sessie["persoon"], geheim)
    store.zet_totp_teller(sessie["persoon"], teller)
    return _json(h, 200, {"totp": True})


def totp_uit(h, sessie):
    store.zet_totp(sessie["persoon"], None)
    return _json(h, 200, {"totp": False})


def route(h, pad, sessie, body=None):
    """True wanneer dit pad hier hoort en is afgehandeld."""
    if body is None:
        return False
    if pad == "/api/uitnodiging":
        return uitnodigen(h, sessie)
    if pad == "/api/uitnodiging/intrekken":
        return uitnodigingen_intrekken(h, sessie)
    if pad == "/api/totp/start":
        return totp_starten(h, sessie)
    if pad == "/api/totp/aan":
        return totp_bevestigen(h, sessie, body)
    if pad == "/api/totp/uit":
        return totp_uit(h, sessie)
    return False
