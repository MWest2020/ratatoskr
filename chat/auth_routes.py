# SPDX-License-Identifier: EUPL-1.2
"""De HTTP-kant van inloggen: routes die géén sessie vereisen, plus de gate.

`server.py` blijft dun: het roept `open_route()` voor de paden die zonder
sessie mogen, en `gate()` voor al het andere onder /api/.

Antwoorden zijn opzettelijk karig. Een onbekende naam en een fout wachtwoord
geven hetzelfde: "inloggen mislukt". Wie wil weten of een naam bestaat, komt er
hier niet achter.
"""
import json
import os

import auth
import auth_rem as rem
import auth_store as store
import instellingen

MISLUKT = {"error": "inloggen mislukt"}

# Paden die zonder sessie moeten kunnen — anders kun je nooit inloggen.
OPEN = ("/api/login", "/api/setup", "/api/uitnodiging/gebruik", "/api/status")


def _bron(h):
    """Het adres waar dit verzoek vandaan komt, voor de rem. Achter een reverse
    proxy is dat de proxy, dus X-Forwarded-For gaat voor."""
    doorgestuurd = (h.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return doorgestuurd or h.client_address[0]


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
    return _json(h, 200, {"personen": store.aantal_personen()})


def sessie_info(h):
    s = auth.sessie_uit_cookie(h.headers)
    if s is None:
        return _json(h, 401, {"error": "geen sessie"})
    p = store.persoon(s["persoon"])
    return _json(h, 200, {"naam": p["naam"], "eigenaar": bool(p["eigenaar"]),
                          "csrf": s["csrf"], "totp": bool(p["totp"])})


def inloggen(h, body):
    naam = (body.get("naam") or "").strip()
    wachtwoord = body.get("wachtwoord") or ""
    sleutels = ["naam:" + naam.lower(), "bron:" + _bron(h)]
    wacht = max(rem.poging_geblokkeerd(s) for s in sleutels)
    if wacht:
        return _json(h, 429, {"error": "te veel pogingen", "wacht": wacht})

    p = store.persoon_op_naam(naam) if naam else None
    # Ook bij een onbekende naam een hash uitrekenen: anders verraadt de
    # antwoordtijd of het account bestaat.
    opgeslagen = p["hash"] if p else auth.hash_wachtwoord("x", n=2 ** 14)
    goed = auth.wachtwoord_klopt(wachtwoord, opgeslagen) and p is not None

    if not goed:
        for s in sleutels:
            rem.noteer_mislukking(s)
        return _json(h, 401, MISLUKT)

    if p["totp"]:
        code = (body.get("code") or "").strip()
        if not code:
            # Naam en wachtwoord klopten; dat de app nu om een code vraagt lekt
            # niets extra's. Geen mislukking tellen: dan zou elke login met
            # tweede factor de rem aanzetten.
            return _json(h, 401, {"error": "code nodig", "totp": True})
        ok, teller = auth.totp_klopt(p["totp"], code, laatste=p["totp_laatste"])
        if not ok:
            for s in sleutels:
                rem.noteer_mislukking(s)
            return _json(h, 401, {"error": "inloggen mislukt", "totp": True})
        store.zet_totp_teller(p["id"], teller)

    for s in sleutels:
        rem.wis_pogingen(s)
    if auth.verouderd(p["hash"]):
        store.zet_hash(p["id"], auth.hash_wachtwoord(wachtwoord))
    token, csrf = auth.start_sessie(p["id"])
    return _json(h, 200, {"naam": p["naam"], "csrf": csrf},
                 [("Set-Cookie", auth.cookie_kop(token, h.headers.get("Host", "")))])


def uitloggen(h, body):
    auth.stop_sessie(h.headers, overal=bool(body.get("overal")))
    return _json(h, 200, {"status": "uitgelogd"},
                 [("Set-Cookie", auth.cookie_kop("", h.headers.get("Host", ""),
                                                 verwijder=True))])


def _maak_account(h, naam, wachtwoord, eigenaar):
    naam = (naam or "").strip()
    if len(naam) < 2 or len(wachtwoord or "") < 12:
        return _json(h, 400, {"error": "naam minstens 2 tekens, wachtwoord minstens 12"})
    pid = store.maak_persoon(naam, auth.hash_wachtwoord(wachtwoord), eigenaar)
    if pid is None:
        return _json(h, 409, {"error": "die naam bestaat al"})
    token, csrf = auth.start_sessie(pid)
    return _json(h, 201, {"naam": naam, "csrf": csrf},
                 [("Set-Cookie", auth.cookie_kop(token, h.headers.get("Host", "")))])


def setup(h, body):
    """De eerste persoon. Alleen zolang er niemand is."""
    if store.aantal_personen() > 0:
        return _json(h, 403, {"error": "er is al een account"})
    token = body.get("token") or ""
    # Twee sleutels passen: de afgedrukte setup-link, en éénmalig het oude
    # gedeelde schrijf-token van een bestaande installatie.
    if not (auth.uitnodiging_geldig(token, "setup") or auth.setup_token_geldig(token)):
        rem.noteer_mislukking("bron:" + _bron(h))
        return _json(h, 403, {"error": "ongeldige of verlopen setup-link"})
    antwoord = _maak_account(h, body.get("naam"), body.get("wachtwoord"), eigenaar=True)
    auth.gebruik_uitnodiging(token)      # eenmalig, ook als het het oude token was
    store.trek_uitnodigingen_in("setup")
    return antwoord


def uitnodiging_gebruiken(h, body):
    token = body.get("token") or ""
    if not auth.uitnodiging_geldig(token, "uitnodiging"):
        rem.noteer_mislukking("bron:" + _bron(h))
        return _json(h, 403, {"error": "ongeldige of verlopen uitnodiging"})
    if not auth.gebruik_uitnodiging(token):     # markeer eerst: eenmalig, ook bij een race
        return _json(h, 403, {"error": "ongeldige of verlopen uitnodiging"})
    return _maak_account(h, body.get("naam"), body.get("wachtwoord"), eigenaar=False)


def open_route(h, pad, body=None):
    """Routes die zonder sessie mogen. True = afgehandeld."""
    if pad == "/api/status":
        return status(h)
    if pad == "/api/login" and body is not None:
        return inloggen(h, body)
    if pad == "/api/setup" and body is not None:
        return setup(h, body)
    if pad == "/api/uitnodiging/gebruik" and body is not None:
        return uitnodiging_gebruiken(h, body)
    return False


def gate(h, pad, schrijft):
    """De sessiecontrole. Geeft de sessierij terug, of None als er al een
    antwoord verstuurd is."""
    s = auth.sessie_uit_cookie(h.headers)
    if s is None:
        _json(h, 401, {"error": "inloggen vereist"})
        return None
    if schrijft and not auth.csrf_klopt(h.headers, s):
        _json(h, 403, {"error": "ontbrekend of ongeldig sessietoken"})
        return None
    return s


def setup_link_bij_start():
    """Bij een verse installatie: druk een eenmalige setup-link af.

    Geen standaardwachtwoord — dat is het ding waar elk zelfgehost product op
    stukloopt. Bestaat er al een oud gedeeld schrijf-token, dan zeggen we dat
    dat éénmalig ook werkt.
    """
    if store.aantal_personen() > 0:
        return
    store.trek_uitnodigingen_in("setup")
    token = auth.nieuwe_uitnodiging("setup")
    basis = instellingen.lees("URL").rstrip("/")
    print("[chat] nog geen account. Maak de eigenaar aan via:", flush=True)
    print("[chat]   {}/login?setup={}".format(basis or "<jouw boomhuis-url>", token),
          flush=True)
    if instellingen.lees("APP_TOKEN").strip():
        print("[chat]   (of eenmalig met het oude APP_TOKEN)", flush=True)
