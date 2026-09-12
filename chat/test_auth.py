# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor inloggen (chat/auth.py).

Draaien vanuit chat/: `python3 -m unittest test_auth`. Geen relay of netwerk
nodig; de database is een tijdelijk bestand.
"""
import os
import tempfile
import time
import unittest

os.environ.setdefault("BOOMHUIS_AUTH_DB", os.path.join(tempfile.mkdtemp(), "auth.db"))

import auth  # noqa: E402
import auth_store as store  # noqa: E402


class Passwords(unittest.TestCase):
    def test_matches_and_does_not_match(self):
        h = auth.hash_password("een lang genoeg wachtwoord", n=2 ** 12)
        self.assertTrue(auth.password_matches("een lang genoeg wachtwoord", h))
        self.assertFalse(auth.password_matches("iets anders", h))

    def test_same_password_gives_a_different_hash(self):
        """Elk account zijn eigen salt, anders verraden gelijke hashes gelijke
        wachtwoorden."""
        a = auth.hash_password("hetzelfde wachtwoord", n=2 ** 12)
        b = auth.hash_password("hetzelfde wachtwoord", n=2 ** 12)
        self.assertNotEqual(a, b)

    def test_lighter_parameters_count_as_outdated(self):
        self.assertTrue(auth.outdated(auth.hash_password("x" * 12, n=2 ** 12)))
        self.assertFalse(auth.outdated(auth.hash_password("x" * 12)))

    def test_the_configured_parameters_really_run(self):
        """scrypt weigert boven OpenSSL's geheugengrens (32 MB) met "memory
        limit exceeded". Met N=2**15 gebeurde dat precies — dat merk je pas bij
        de eerste echte login, dus staat het hier."""
        h = auth.hash_password("een wachtwoord van genoeg tekens")
        self.assertTrue(auth.password_matches("een wachtwoord van genoeg tekens", h))

    def test_a_broken_hash_grants_no_access(self):
        for junk in ("", "geen$hash", "argon2$1$2$3$4$5", None):
            self.assertFalse(auth.password_matches("wat dan ook", junk))


class SecondFactor(unittest.TestCase):
    def test_code_matches_within_the_drift(self):
        secret = auth.new_totp_secret()
        now = time.time()
        code = auth._totp(secret, int(now // 30))
        self.assertTrue(auth.totp_matches(secret, code, now=now)[0])

    def test_a_code_cannot_be_used_twice(self):
        secret = auth.new_totp_secret()
        now = time.time()
        code = auth._totp(secret, int(now // 30))
        ok, counter = auth.totp_matches(secret, code, now=now)
        self.assertTrue(ok)
        self.assertFalse(auth.totp_matches(secret, code, last=counter, now=now)[0])

    def test_nonsense_is_refused(self):
        secret = auth.new_totp_secret()
        for code in ("", "abcdef", "12345", None):
            self.assertFalse(auth.totp_matches(secret, code)[0])


class Sessions(unittest.TestCase):
    def setUp(self):
        self.pid = store.create_person("sessietest-" + os.urandom(4).hex(), "hash")

    def test_a_session_lives_and_can_be_revoked(self):
        token, csrf = auth.start_session(self.pid)
        headers = {"Cookie": "{}={}".format(auth.COOKIE, token)}
        self.assertIsNotNone(auth.session_from_cookie(headers))
        auth.stop_session(headers)
        self.assertIsNone(auth.session_from_cookie(headers))
        self.assertTrue(csrf)

    def test_an_expired_session_does_not_count(self):
        token, _ = auth.start_session(self.pid)
        store.create_session(auth._hash(token), self.pid, "x", store.now() - 1)
        headers = {"Cookie": "{}={}".format(auth.COOKIE, token)}
        self.assertIsNone(auth.session_from_cookie(headers))

    def test_logging_out_everywhere_hits_every_device(self):
        first, _ = auth.start_session(self.pid)
        second, _ = auth.start_session(self.pid)
        auth.stop_session({"Cookie": "{}={}".format(auth.COOKIE, first)}, everywhere=True)
        self.assertIsNone(auth.session_from_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, second)}))

    def test_only_the_hash_is_in_the_database(self):
        """Wie het bestand leest heeft daar geen bruikbare sessie aan."""
        token, _ = auth.start_session(self.pid)
        with store._connect() as con:
            rows = [r["hash"] for r in con.execute("SELECT hash FROM sessies")]
        self.assertNotIn(token, rows)
        self.assertIn(auth._hash(token), rows)

    def test_csrf_must_match(self):
        token, csrf = auth.start_session(self.pid)
        session = auth.session_from_cookie({"Cookie": "{}={}".format(auth.COOKIE, token)})
        self.assertTrue(auth.csrf_matches({auth.CSRF_HEADER: csrf}, session))
        self.assertFalse(auth.csrf_matches({auth.CSRF_HEADER: "iets anders"}, session))
        self.assertFalse(auth.csrf_matches({}, session))


class Cookie(unittest.TestCase):
    def test_secure_outside_localhost(self):
        self.assertIn("Secure", auth.cookie_header("t", "boomhuis-relay.tail8f7877.ts.net"))
        self.assertNotIn("Secure", auth.cookie_header("t", "localhost:8090"))

    def test_always_httponly_and_samesite(self):
        header = auth.cookie_header("t", "localhost")
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Lax", header)


class Invites(unittest.TestCase):
    def test_works_exactly_once(self):
        token = auth.new_invite("uitnodiging")
        self.assertTrue(auth.invite_valid(token, "uitnodiging"))
        self.assertTrue(auth.use_invite(token))
        self.assertFalse(auth.use_invite(token))
        self.assertFalse(auth.invite_valid(token, "uitnodiging"))

    def test_the_kind_must_match(self):
        """Een setup-link is geen uitnodiging: anders maakt de tweede persoon
        zichzelf eigenaar."""
        token = auth.new_invite("setup")
        self.assertFalse(auth.invite_valid(token, "uitnodiging"))

    def test_an_expired_invite_does_not_count(self):
        token = auth.new_invite("uitnodiging")
        store.create_invite(auth._hash(token), "uitnodiging", store.now() - 1)
        self.assertFalse(auth.invite_valid(token, "uitnodiging"))


class OldToken(unittest.TestCase):
    """Het migratiepad: zolang er niemand is mag het oude gedeelde token de
    eigenaar aanmaken. Zodra er iemand is, nooit meer."""

    def setUp(self):
        self._old = os.environ.get("BOOMHUIS_APP_TOKEN")
        os.environ["BOOMHUIS_APP_TOKEN"] = "oud-gedeeld-token"

    def tearDown(self):
        if self._old is None:
            os.environ.pop("BOOMHUIS_APP_TOKEN", None)
        else:
            os.environ["BOOMHUIS_APP_TOKEN"] = self._old

    def test_no_longer_once_someone_exists(self):
        store.create_person("iemand-" + os.urandom(4).hex(), "hash")
        self.assertFalse(auth.setup_token_valid("oud-gedeeld-token"))


if __name__ == "__main__":
    unittest.main()
