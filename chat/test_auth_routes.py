# SPDX-License-Identifier: MIT
"""Tests for the HTTP side of logging in (chat/auth_routes.py).

Without a server: the routes get a stand-in handler that records what would have
been sent. What has to be proven here is not "it works" but "it refuses" — no
session, wrong password, no CSRF, a spent invitation.
"""
import json
import os
import tempfile
import unittest

os.environ.setdefault("BOOMHUIS_AUTH_DB", os.path.join(tempfile.mkdtemp(), "auth.db"))

import auth  # noqa: E402
import auth_factors  # noqa: E402
import auth_routes as routes  # noqa: E402
import auth_store as store  # noqa: E402


class _Handler:
    """Just enough of BaseHTTPRequestHandler to run the routes."""

    def __init__(self, headers=None, source="10.0.0.1"):
        self.headers = headers or {}
        self.client_address = (source, 1234)
        self.code = None
        self.payload = None
        self.set_cookie = []
        self._buffer = b""

    # the routes use these four
    def send_response(self, code):
        self.code = code

    def send_header(self, k, v):
        if k == "Set-Cookie":
            self.set_cookie.append(v)

    def end_headers(self):
        pass

    @property
    def wfile(self):
        return self

    def write(self, data):
        self.payload = json.loads(data)


def _post(fn, body, headers=None, source="10.0.0.1"):
    h = _Handler(headers, source)
    fn(h, body)
    return h


class LogIn(unittest.TestCase):
    """Every case its own account AND its own source address: failed attempts
    throttle both the name and the address, so tests that share those block each
    other. That is the behaviour we want — just not in the way."""

    def setUp(self):
        self.name = "route-" + os.urandom(4).hex()
        self.source = "10.{}.{}.{}".format(*os.urandom(3))
        self.pid = store.create_person(self.name, auth_factors.hash_password("een goed wachtwoord"))

    def test_a_good_password_gives_a_cookie(self):
        h = _post(routes.log_in, {"naam": self.name, "wachtwoord": "een goed wachtwoord"},
                  source=self.source)
        self.assertEqual(h.code, 200)
        self.assertTrue(h.set_cookie and auth.COOKIE in h.set_cookie[0])
        self.assertIn("csrf", h.payload)

    def test_wrong_password_and_unknown_name_are_indistinguishable(self):
        wrong = _post(routes.log_in, {"naam": self.name, "wachtwoord": "mis"},
                      source=self.source)
        unknown = _post(routes.log_in, {"naam": "bestaat-niet-" + os.urandom(3).hex(),
                                        "wachtwoord": "mis"},
                        source="10.{}.{}.{}".format(*os.urandom(3)))
        self.assertEqual(wrong.code, unknown.code)
        self.assertEqual(wrong.payload, unknown.payload)
        self.assertEqual(wrong.code, 401)

    def test_no_cookie_on_a_failed_attempt(self):
        h = _post(routes.log_in, {"naam": self.name, "wachtwoord": "mis"}, source=self.source)
        self.assertEqual(h.set_cookie, [])

    def test_the_throttle_kicks_in(self):
        for _ in range(6):
            _post(routes.log_in, {"naam": self.name, "wachtwoord": "mis"}, source=self.source)
        # Even WITH the right password: the brake comes before the check,
        # otherwise it is not a brake but a delay.
        h = _post(routes.log_in, {"naam": self.name, "wachtwoord": "een goed wachtwoord"},
                  source=self.source)
        self.assertEqual(h.code, 429)
        self.assertGreater(h.payload.get("wacht", 0), 0)


class Gate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pid = store.create_person("gate-" + os.urandom(4).hex(), "hash")

    def test_no_session_no_access_not_even_for_reading(self):
        h = _Handler()
        self.assertIsNone(routes.gate(h, "/api/channels", writes=False))
        self.assertEqual(h.code, 401)

    def test_with_a_session_reading_is_allowed(self):
        token, _ = auth.start_session(self.pid)
        h = _Handler({"Cookie": "{}={}".format(auth.COOKIE, token)})
        self.assertIsNotNone(routes.gate(h, "/api/channels", writes=False))

    def test_writing_without_a_session_token_is_refused(self):
        token, _ = auth.start_session(self.pid)
        h = _Handler({"Cookie": "{}={}".format(auth.COOKIE, token)})
        self.assertIsNone(routes.gate(h, "/api/send", writes=True))
        self.assertEqual(h.code, 403)

    def test_writing_with_a_session_token_is_allowed(self):
        token, csrf = auth.start_session(self.pid)
        h = _Handler({"Cookie": "{}={}".format(auth.COOKIE, token),
                      auth.CSRF_HEADER: csrf})
        self.assertIsNotNone(routes.gate(h, "/api/send", writes=True))


class Inviting(unittest.TestCase):
    def test_an_invite_works_once(self):
        token = auth.new_invite("uitnodiging")
        name = "gast-" + os.urandom(4).hex()
        first = _post(routes.use_invite,
                      {"token": token, "naam": name, "wachtwoord": "lang genoeg hoor"})
        self.assertEqual(first.code, 201)
        second = _post(routes.use_invite,
                       {"token": token, "naam": name + "2", "wachtwoord": "lang genoeg hoor"})
        self.assertEqual(second.code, 403)

    def test_a_short_password_is_refused(self):
        token = auth.new_invite("uitnodiging")
        h = _post(routes.use_invite,
                  {"token": token, "naam": "kort", "wachtwoord": "kort"})
        self.assertEqual(h.code, 400)

    def test_setup_is_gone_once_someone_exists(self):
        store.create_person("er-is-iemand-" + os.urandom(4).hex(), "hash")
        h = _post(routes.setup, {"token": "wat dan ook", "naam": "x", "wachtwoord": "y" * 12})
        self.assertEqual(h.code, 403)


if __name__ == "__main__":
    unittest.main()


class ChangePassword(unittest.TestCase):
    """Your own password, with the current one alongside: otherwise a borrowed
    session is enough to lock someone out permanently."""

    def setUp(self):
        import auth_admin
        self.admin = auth_admin
        self.name = "ww-" + os.urandom(4).hex()
        self.pid = store.create_person(self.name, auth_factors.hash_password("het oude wachtwoord"))
        self.token, self.csrf = auth.start_session(self.pid)
        self.session = auth.session_from_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, self.token)})

    def _change(self, current, new):
        h = _Handler()
        self.admin.change_password(h, self.session, {"huidig": current, "nieuw": new})
        return h

    def test_not_without_the_current_password(self):
        h = self._change("iets anders", "een nieuw lang wachtwoord")
        self.assertEqual(h.code, 403)
        self.assertTrue(auth_factors.password_matches("het oude wachtwoord",
                                              store.person(self.pid)["hash"]))

    def test_not_a_too_short_new_password(self):
        h = self._change("het oude wachtwoord", "kort")
        self.assertEqual(h.code, 400)

    def test_changing_revokes_all_sessions_and_gives_a_new_one(self):
        second, _ = auth.start_session(self.pid)    # another device
        h = self._change("het oude wachtwoord", "een nieuw lang wachtwoord")
        self.assertEqual(h.code, 200)
        self.assertTrue(auth_factors.password_matches("een nieuw lang wachtwoord",
                                              store.person(self.pid)["hash"]))
        # the other device is out
        self.assertIsNone(auth.session_from_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, second)}))
        # and this device got a fresh session
        self.assertTrue(h.set_cookie and auth.COOKIE in h.set_cookie[0])
        self.assertIn("csrf", h.payload)
