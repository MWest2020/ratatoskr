# SPDX-License-Identifier: EUPL-1.2
"""The two login factors: a password (scrypt) and a TOTP code (RFC 6238).

All standard library: `hashlib.scrypt` for passwords, `hmac` for TOTP, `secrets`
for salts and secrets. No crypto library, because the VM backend is deliberately
dependency-free — and hand-rolled crypto is exactly the clever trap this project
warns against.

Pure functions: nothing here reads or writes the database. Storing the hash and
the last used TOTP counter is the caller's job (auth_routes, auth_admin).
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time


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
