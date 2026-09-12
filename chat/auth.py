# SPDX-License-Identifier: EUPL-1.2
"""Who is this, and may they be here.

All standard library: `hashlib.scrypt` for passwords, `hmac` for TOTP (RFC 6238),
`secrets` for sessions. No crypto library, because the VM backend is deliberately
dependency-free — and hand-rolled crypto is exactly the clever trap this project
warns against. Passkeys and OIDC arrive as a second credential on top of the same
session layer; see the change `inloggen-per-persoon`.

The shared write token from the previous version is gone as an authentication
means; it may only create the owner, once (`setup_token_valid`).
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
SESSION_TTL = 30 * 24 * 3600      # extended on use; a PWA you open weekly should
                                  # not ask again every single time
INVITE_TTL = 7 * 24 * 3600
SETUP_TTL = 24 * 3600

# Today's parameters. They sit next to every hash, so they can go up without
# locking anyone out: on a successful login with older parameters the hash is
# recomputed.
#
# N=2**14 and no higher, for two reasons you only notice when running it: scrypt
# uses 128*N*r bytes (16 MB here), and OpenSSL refuses above 32 MB with "memory
# limit exceeded" — 2**15 falls just outside. And every concurrent login really
# costs that memory, so it is also a brake on how many login attempts an
# installation can take at once.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1


# --- passwords --------------------------------------------------------------

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
    """True when this hash was made with lighter parameters than we want now."""
    try:
        n, r, p, _, _ = _parse(stored)
    except (ValueError, TypeError):
        return True
    return (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P)


# --- second factor (TOTP, RFC 6238) -----------------------------------------

def new_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _totp(secret, counter):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return "{:06d}".format(code % 1_000_000)


def totp_matches(secret, code, last=None, now=None, drift=1):
    """Valid within ±`drift` steps. Returns (ok, counter); that counter must be
    stored, otherwise the same code can be used twice."""
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


# --- sessions ---------------------------------------------------------------

def _hash(token):
    """Only the hash is in the database: whoever reads the file gets no usable
    session out of it."""
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(pid):
    """Returns (session token, csrf token). We never see the token itself again."""
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    store.create_session(_hash(token), pid, csrf, store.now() + SESSION_TTL)
    return token, csrf


def session_from_cookie(headers):
    """The session row for this request, or None. Extends it along the way."""
    token = _cookie(headers, COOKIE)
    if not token:
        return None
    row = store.session(_hash(token))
    if row is None:
        return None
    # Extend on use, but do not write on every request: that would be one write
    # per four-second poll.
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
    """Set-Cookie. Secure is left off on localhost, otherwise you cannot develop
    locally; everywhere else it is on."""
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


# --- first start and invitations --------------------------------------------

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
    """Migration path: as long as there is nobody, the old shared write token may
    create the owner. Never again after that — there is a person by then."""
    old = settings.read("APP_TOKEN").strip()
    if not old or store.person_count() > 0:
        return False
    return hmac.compare_digest(token or "", old)
