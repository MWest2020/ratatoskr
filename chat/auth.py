# SPDX-License-Identifier: EUPL-1.2
"""Wie is dit, en mag die hier zijn.

Alles met de standaardbibliotheek: `hashlib.scrypt` voor wachtwoorden, `hmac`
voor TOTP (RFC 6238), `secrets` voor sessies. Geen cryptobibliotheek, want de
VM-backend is bewust dependency-loos — en zelfgeschreven crypto is precies de
slimme valkuil waar dit project tegen waarschuwt. Passkeys en OIDC komen als
tweede credential bovenop dezelfde sessielaag; zie de change `inloggen-per-persoon`.

Het gedeelde schrijf-token uit de vorige versie is weg als authenticatiemiddel;
het mag alleen nog éénmalig de eigenaar aanmaken (`setup_token_valid`).
"""
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time

import auth_store as store
import settings

COOKIE = "bh_session"
CSRF_HEADER = "X-CSRF-Token"
SESSION_TTL = 30 * 24 * 3600      # verlengd bij gebruik; een PWA die je wekelijks
                                  # opent hoort niet elke keer opnieuw te vragen
INVITE_TTL = 7 * 24 * 3600
SETUP_TTL = 24 * 3600

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

def hash_password(password, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P):
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        n, r, p, base64.b64encode(salt).decode(), base64.b64encode(derived).decode())


def _parse(stored):
    if not isinstance(stored, str):
        raise ValueError("geen hash")
    kind, n, r, p, salt, hsh = stored.split("$")
    if kind != "scrypt":
        raise ValueError("onbekende hashsoort")
    return int(n), int(r), int(p), base64.b64decode(salt), base64.b64decode(hsh)


def password_matches(password, stored):
    try:
        n, r, p, salt, expected = _parse(stored)
    except (ValueError, TypeError):
        return False
    derived = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p,
                             dklen=len(expected))
    return hmac.compare_digest(derived, expected)


def outdated(stored):
    """True wanneer deze hash met lichtere parameters is gemaakt dan we nu willen."""
    try:
        n, r, p, _, _ = _parse(stored)
    except (ValueError, TypeError):
        return True
    return (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P)


# --- tweede factor (TOTP, RFC 6238) -----------------------------------------

def new_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _totp(secret, counter):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return "{:06d}".format(code % 1_000_000)


def totp_matches(secret, code, last=None, now=None, drift=1):
    """Geldig binnen ±`drift` stappen. Geeft (ok, counter) terug; die counter
    moet bewaard worden, anders is dezelfde code twee keer bruikbaar."""
    if not code or not code.strip().isdigit():
        return False, None
    code = code.strip()
    current = int((now if now is not None else time.time()) // 30)
    for step in range(-drift, drift + 1):
        counter = current + step
        if last is not None and counter <= last:
            continue
        if hmac.compare_digest(_totp(secret, counter), code):
            return True, counter
    return False, None


# --- sessies ----------------------------------------------------------------

def _hash(token):
    """In de database staat alleen de hash: wie het bestand leest, heeft daar
    geen bruikbare sessie aan."""
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(pid):
    """Geeft (sessietoken, csrf-token). Het token zelf zien we hierna nooit meer."""
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    store.create_session(_hash(token), pid, csrf, store.now() + SESSION_TTL)
    return token, csrf


def session_from_cookie(headers):
    """De sessierij bij dit verzoek, of None. Verlengt en passant."""
    token = _cookie(headers, COOKIE)
    if not token:
        return None
    row = store.session(_hash(token))
    if row is None:
        return None
    # Verlengen bij gebruik, maar niet bij elk verzoek schrijven: dat is een
    # write per poll van vier seconden.
    if store.now() - row["gezien"] > 3600:
        store.extend_session(row["hash"], store.now() + SESSION_TTL)
    return row


def stop_session(headers, everywhere=False):
    token = _cookie(headers, COOKIE)
    if not token:
        return
    row = store.session(_hash(token))
    if row is None:
        return
    if everywhere:
        store.revoke_all_sessions(row["persoon"])
    else:
        store.revoke_session(row["hash"])


def _cookie(headers, name):
    raw = headers.get("Cookie") or ""
    for part in raw.split(";"):
        k, _, v = part.strip().partition("=")
        if k == name:
            return v
    return ""


def cookie_header(token, host, delete=False):
    """Set-Cookie. Secure blijft weg op localhost, anders kun je niet lokaal
    ontwikkelen; overal elders staat hij aan."""
    local = host.split(":")[0] in ("localhost", "127.0.0.1", "[::1]")
    parts = ["{}={}".format(COOKIE, "" if delete else token),
             "Path=/", "HttpOnly", "SameSite=Lax"]
    if not local:
        parts.append("Secure")
    parts.append("Max-Age=0" if delete else "Max-Age={}".format(SESSION_TTL))
    return "; ".join(parts)


def csrf_matches(headers, session):
    sent = headers.get(CSRF_HEADER) or ""
    return bool(session) and hmac.compare_digest(sent, session["csrf"])


# --- eerste start en uitnodigingen ------------------------------------------

def new_invite(kind="uitnodiging"):
    ttl = SETUP_TTL if kind == "setup" else INVITE_TTL
    token = secrets.token_urlsafe(32)
    store.create_invite(_hash(token), kind, store.now() + ttl)
    return token


def invite_valid(token, kind=None):
    row = store.invite(_hash(token or ""))
    return bool(row) and (kind is None or row["soort"] == kind)


def use_invite(token):
    return store.use_invite(_hash(token or ""))


def setup_token_valid(token):
    """Migratiepad: zolang er niemand is, mag het oude gedeelde schrijf-token
    de eigenaar aanmaken. Daarna nooit meer — er is dan een persoon."""
    old = settings.read("APP_TOKEN").strip()
    if not old or store.person_count() > 0:
        return False
    return hmac.compare_digest(token or "", old)
