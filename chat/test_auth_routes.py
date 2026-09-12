# SPDX-License-Identifier: EUPL-1.2
"""Tests voor de HTTP-kant van inloggen (chat/auth_routes.py).

Zonder server: de routes krijgen een stand-in van de handler die opschrijft wat
er verstuurd zou zijn. Wat hier bewezen moet worden is niet "het werkt" maar
"het weigert" — geen sessie, verkeerd wachtwoord, geen CSRF, gebruikte
uitnodiging.
"""
import json
import os
import tempfile
import unittest

os.environ.setdefault("BOOMHUIS_AUTH_DB", os.path.join(tempfile.mkdtemp(), "auth.db"))

import auth  # noqa: E402
import auth_routes as routes  # noqa: E402
import auth_store as store  # noqa: E402


class _Handler:
    """Genoeg van BaseHTTPRequestHandler om de routes te draaien."""

    def __init__(self, headers=None, source="10.0.0.1"):
        self.headers = headers or {}
        self.client_address = (source, 1234)
        self.code = None
        self.payload = None
        self.set_cookie = []
        self._buffer = b""

    # de routes gebruiken deze vier
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
    """Elk geval zijn eigen account én eigen bron-adres: mislukte pogingen
    remmen zowel de naam als het adres af, dus tests die dat delen zetten
    elkaar klem. Dat is het gedrag dat we willen — maar niet in de weg."""

    def setUp(self):
        self.name = "route-" + os.urandom(4).hex()
        self.source = "10.{}.{}.{}".format(*os.urandom(3))
        self.pid = store.create_person(self.name, auth.hash_password("een goed wachtwoord"))

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
        # Zelfs mét het juiste wachtwoord: de rem gaat vóór de controle, anders
        # is hij geen rem maar een vertraging.
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
    """Je eigen wachtwoord, mét het huidige erbij: anders is een geleende
    sessie genoeg om iemand permanent buiten te sluiten."""

    def setUp(self):
        import auth_admin
        self.admin = auth_admin
        self.name = "ww-" + os.urandom(4).hex()
        self.pid = store.create_person(self.name, auth.hash_password("het oude wachtwoord"))
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
        self.assertTrue(auth.password_matches("het oude wachtwoord",
                                              store.person(self.pid)["hash"]))

    def test_not_a_too_short_new_password(self):
        h = self._change("het oude wachtwoord", "kort")
        self.assertEqual(h.code, 400)

    def test_changing_revokes_all_sessions_and_gives_a_new_one(self):
        second, _ = auth.start_session(self.pid)    # ander apparaat
        h = self._change("het oude wachtwoord", "een nieuw lang wachtwoord")
        self.assertEqual(h.code, 200)
        self.assertTrue(auth.password_matches("een nieuw lang wachtwoord",
                                              store.person(self.pid)["hash"]))
        # het andere apparaat is eruit
        self.assertIsNone(auth.session_from_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, second)}))
        # en dit apparaat kreeg een verse sessie mee
        self.assertTrue(h.set_cookie and auth.COOKIE in h.set_cookie[0])
        self.assertIn("csrf", h.payload)
