# SPDX-License-Identifier: EUPL-1.2
"""Offline tests for sessions, cookies and invitations (chat/auth.py). Passwords
and TOTP are in test_auth_factors.py.

Run from chat/: `python3 -m unittest test_auth`. No relay or network needed; the
database is a temporary file.
"""
import os
import tempfile
import unittest

os.environ.setdefault("BOOMHUIS_AUTH_DB", os.path.join(tempfile.mkdtemp(), "auth.db"))

import auth  # noqa: E402
import auth_store as store  # noqa: E402


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
        """Whoever reads the file gets no usable session out of it."""
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
        """A setup link is not an invitation: otherwise the second person makes
        themselves the owner."""
        token = auth.new_invite("setup")
        self.assertFalse(auth.invite_valid(token, "uitnodiging"))

    def test_an_expired_invite_does_not_count(self):
        token = auth.new_invite("uitnodiging")
        store.create_invite(auth._hash(token), "uitnodiging", store.now() - 1)
        self.assertFalse(auth.invite_valid(token, "uitnodiging"))


class OldToken(unittest.TestCase):
    """The migration path: as long as there is nobody the old shared token may
    create the owner. Once someone exists, never again."""

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
