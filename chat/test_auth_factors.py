# SPDX-License-Identifier: EUPL-1.2
"""Offline tests for the two login factors (chat/auth_factors.py): passwords and
TOTP codes. Pure functions, so no database and no network.

Run from chat/: `python3 -m unittest test_auth_factors`.
"""
import time
import unittest

import auth_factors


class Passwords(unittest.TestCase):
    def test_matches_and_does_not_match(self):
        h = auth_factors.hash_password("een lang genoeg wachtwoord", n=2 ** 12)
        self.assertTrue(auth_factors.password_matches("een lang genoeg wachtwoord", h))
        self.assertFalse(auth_factors.password_matches("iets anders", h))

    def test_same_password_gives_a_different_hash(self):
        """Every account its own salt, otherwise equal hashes give away equal
        passwords."""
        a = auth_factors.hash_password("hetzelfde wachtwoord", n=2 ** 12)
        b = auth_factors.hash_password("hetzelfde wachtwoord", n=2 ** 12)
        self.assertNotEqual(a, b)

    def test_lighter_parameters_count_as_outdated(self):
        self.assertTrue(auth_factors.outdated(auth_factors.hash_password("x" * 12, n=2 ** 12)))
        self.assertFalse(auth_factors.outdated(auth_factors.hash_password("x" * 12)))

    def test_the_configured_parameters_really_run(self):
        """scrypt refuses above OpenSSL's memory limit (32 MB) with "memory limit
        exceeded". With N=2**15 that happened exactly — you only notice at the
        first real login, so it is here."""
        h = auth_factors.hash_password("een wachtwoord van genoeg tekens")
        self.assertTrue(auth_factors.password_matches("een wachtwoord van genoeg tekens", h))

    def test_a_broken_hash_grants_no_access(self):
        for junk in ("", "geen$hash", "argon2$1$2$3$4$5", None):
            self.assertFalse(auth_factors.password_matches("wat dan ook", junk))


class SecondFactor(unittest.TestCase):
    def test_code_matches_within_the_drift(self):
        secret = auth_factors.new_totp_secret()
        now = time.time()
        code = auth_factors._totp(secret, int(now // 30))
        self.assertTrue(auth_factors.totp_matches(secret, code, now=now)[0])

    def test_a_code_cannot_be_used_twice(self):
        secret = auth_factors.new_totp_secret()
        now = time.time()
        code = auth_factors._totp(secret, int(now // 30))
        ok, counter = auth_factors.totp_matches(secret, code, now=now)
        self.assertTrue(ok)
        self.assertFalse(auth_factors.totp_matches(secret, code, last=counter, now=now)[0])

    def test_nonsense_is_refused(self):
        secret = auth_factors.new_totp_secret()
        for code in ("", "abcdef", "12345", None):
            self.assertFalse(auth_factors.totp_matches(secret, code)[0])


if __name__ == "__main__":
    unittest.main()
