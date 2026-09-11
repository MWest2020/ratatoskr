# SPDX-License-Identifier: EUPL-1.2
"""Wie is dit, en mag die hier zijn.

Alles met de standaardbibliotheek: `hashlib.scrypt` voor wachtwoorden, `hmac`
voor TOTP (RFC 6238), `secrets` voor sessies. Geen cryptobibliotheek, want de
VM-backend is bewust dependency-loos — en zelfgeschreven crypto is precies de
slimme valkuil waar dit project tegen waarschuwt. Passkeys en OIDC komen als
tweede credential bovenop dezelfde sessielaag; zie de change `inloggen-per-persoon`.

Het gedeelde schrijf-token uit de vorige versie is weg als authenticatiemiddel;
het mag alleen nog éénmalig de eigenaar aanmaken (`setup_token_geldig`).
"""
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time

import auth_store as store
import instellingen

COOKIE = "bh_session"
CSRF_HEADER = "X-CSRF-Token"
SESSIE_DUUR = 30 * 24 * 3600      # verlengd bij gebruik; een PWA die je wekelijks
                                  # opent hoort niet elke keer opnieuw te vragen
UITNODIGING_DUUR = 7 * 24 * 3600
SETUP_DUUR = 24 * 3600

# Parameters van vandaag. Ze staan bij elke hash, dus ze kunnen omhoog zonder
# iemand buiten te sluiten: bij een geslaagde login met oudere parameters wordt
# de hash herberekend.
#
# N=2**14 en niet hoger, om twee redenen die je pas bij het draaien merkt:
# scrypt gebruikt 128*N*r bytes (hier 16 MB), en OpenSSL weigert boven de 32 MB
# met "memory limit exceeded" — 2**15 valt daar precies buiten. En elke
# gelijktijdige login kost dat geheugen echt, dus het is ook een rem op hoeveel
# inlogpogingen een installatie tegelijk aankan.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1


# --- wachtwoorden -----------------------------------------------------------

def hash_wachtwoord(wachtwoord, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P):
    zout = secrets.token_bytes(16)
    afgeleid = hashlib.scrypt(wachtwoord.encode(), salt=zout, n=n, r=r, p=p, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        n, r, p, base64.b64encode(zout).decode(), base64.b64encode(afgeleid).decode())


def _ontleed(opgeslagen):
    if not isinstance(opgeslagen, str):
        raise ValueError("geen hash")
    soort, n, r, p, zout, hsh = opgeslagen.split("$")
    if soort != "scrypt":
        raise ValueError("onbekende hashsoort")
    return int(n), int(r), int(p), base64.b64decode(zout), base64.b64decode(hsh)


def wachtwoord_klopt(wachtwoord, opgeslagen):
    try:
        n, r, p, zout, verwacht = _ontleed(opgeslagen)
    except (ValueError, TypeError):
        return False
    afgeleid = hashlib.scrypt(wachtwoord.encode(), salt=zout, n=n, r=r, p=p,
                              dklen=len(verwacht))
    return hmac.compare_digest(afgeleid, verwacht)


def verouderd(opgeslagen):
    """True wanneer deze hash met lichtere parameters is gemaakt dan we nu willen."""
    try:
        n, r, p, _, _ = _ontleed(opgeslagen)
    except (ValueError, TypeError):
        return True
    return (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P)


# --- tweede factor (TOTP, RFC 6238) -----------------------------------------

def nieuw_totp_geheim():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _totp(geheim, teller):
    sleutel = base64.b32decode(geheim + "=" * (-len(geheim) % 8))
    mac = hmac.new(sleutel, struct.pack(">Q", teller), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return "{:06d}".format(code % 1_000_000)


def totp_klopt(geheim, code, laatste=None, nu=None, speling=1):
    """Geldig binnen ±`speling` stappen. Geeft (ok, teller) terug; die teller
    moet bewaard worden, anders is dezelfde code twee keer bruikbaar."""
    if not code or not code.strip().isdigit():
        return False, None
    code = code.strip()
    huidig = int((nu if nu is not None else time.time()) // 30)
    for stap in range(-speling, speling + 1):
        teller = huidig + stap
        if laatste is not None and teller <= laatste:
            continue
        if hmac.compare_digest(_totp(geheim, teller), code):
            return True, teller
    return False, None


# --- sessies ----------------------------------------------------------------

def _hash(token):
    """In de database staat alleen de hash: wie het bestand leest, heeft daar
    geen bruikbare sessie aan."""
    return hashlib.sha256(token.encode()).hexdigest()


def start_sessie(pid):
    """Geeft (sessietoken, csrf-token). Het token zelf zien we hierna nooit meer."""
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    store.maak_sessie(_hash(token), pid, csrf, store.nu() + SESSIE_DUUR)
    return token, csrf


def sessie_uit_cookie(headers):
    """De sessierij bij dit verzoek, of None. Verlengt en passant."""
    token = _cookie(headers, COOKIE)
    if not token:
        return None
    rij = store.sessie(_hash(token))
    if rij is None:
        return None
    # Verlengen bij gebruik, maar niet bij elk verzoek schrijven: dat is een
    # write per poll van vier seconden.
    if store.nu() - rij["gezien"] > 3600:
        store.verleng_sessie(rij["hash"], store.nu() + SESSIE_DUUR)
    return rij


def stop_sessie(headers, overal=False):
    token = _cookie(headers, COOKIE)
    if not token:
        return
    rij = store.sessie(_hash(token))
    if rij is None:
        return
    if overal:
        store.trek_alle_sessies_in(rij["persoon"])
    else:
        store.trek_sessie_in(rij["hash"])


def _cookie(headers, naam):
    rauw = headers.get("Cookie") or ""
    for stuk in rauw.split(";"):
        k, _, v = stuk.strip().partition("=")
        if k == naam:
            return v
    return ""


def cookie_kop(token, host, verwijder=False):
    """Set-Cookie. Secure blijft weg op localhost, anders kun je niet lokaal
    ontwikkelen; overal elders staat hij aan."""
    lokaal = host.split(":")[0] in ("localhost", "127.0.0.1", "[::1]")
    stukken = ["{}={}".format(COOKIE, "" if verwijder else token),
               "Path=/", "HttpOnly", "SameSite=Lax"]
    if not lokaal:
        stukken.append("Secure")
    stukken.append("Max-Age=0" if verwijder else "Max-Age={}".format(SESSIE_DUUR))
    return "; ".join(stukken)


def csrf_klopt(headers, sessie):
    meegestuurd = headers.get(CSRF_HEADER) or ""
    return bool(sessie) and hmac.compare_digest(meegestuurd, sessie["csrf"])


# --- eerste start en uitnodigingen ------------------------------------------

def nieuwe_uitnodiging(soort="uitnodiging"):
    duur = SETUP_DUUR if soort == "setup" else UITNODIGING_DUUR
    token = secrets.token_urlsafe(32)
    store.maak_uitnodiging(_hash(token), soort, store.nu() + duur)
    return token


def uitnodiging_geldig(token, soort=None):
    rij = store.uitnodiging(_hash(token or ""))
    return bool(rij) and (soort is None or rij["soort"] == soort)


def gebruik_uitnodiging(token):
    return store.gebruik_uitnodiging(_hash(token or ""))


def setup_token_geldig(token):
    """Migratiepad: zolang er niemand is, mag het oude gedeelde schrijf-token
    de eigenaar aanmaken. Daarna nooit meer — er is dan een persoon."""
    oud = instellingen.lees("APP_TOKEN").strip()
    if not oud or store.aantal_personen() > 0:
        return False
    return hmac.compare_digest(token or "", oud)
