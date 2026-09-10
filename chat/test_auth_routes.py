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

    def __init__(self, koppen=None, bron="10.0.0.1"):
        self.headers = koppen or {}
        self.client_address = (bron, 1234)
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


def _post(fn, body, koppen=None, bron="10.0.0.1"):
    h = _Handler(koppen, bron)
    fn(h, body)
    return h


class Inloggen(unittest.TestCase):
    """Elk geval zijn eigen account én eigen bron-adres: mislukte pogingen
    remmen zowel de naam als het adres af, dus tests die dat delen zetten
    elkaar klem. Dat is het gedrag dat we willen — maar niet in de weg."""

    def setUp(self):
        self.naam = "route-" + os.urandom(4).hex()
        self.bron = "10.{}.{}.{}".format(*os.urandom(3))
        self.pid = store.maak_persoon(self.naam, auth.hash_wachtwoord("een goed wachtwoord"))

    def test_goed_wachtwoord_geeft_een_cookie(self):
        h = _post(routes.inloggen, {"naam": self.naam, "wachtwoord": "een goed wachtwoord"},
                  bron=self.bron)
        self.assertEqual(h.code, 200)
        self.assertTrue(h.set_cookie and auth.COOKIE in h.set_cookie[0])
        self.assertIn("csrf", h.payload)

    def test_fout_wachtwoord_en_onbekende_naam_zijn_niet_te_onderscheiden(self):
        fout = _post(routes.inloggen, {"naam": self.naam, "wachtwoord": "mis"},
                     bron=self.bron)
        onbekend = _post(routes.inloggen, {"naam": "bestaat-niet-" + os.urandom(3).hex(),
                                           "wachtwoord": "mis"},
                         bron="10.{}.{}.{}".format(*os.urandom(3)))
        self.assertEqual(fout.code, onbekend.code)
        self.assertEqual(fout.payload, onbekend.payload)
        self.assertEqual(fout.code, 401)

    def test_geen_cookie_bij_een_mislukte_poging(self):
        h = _post(routes.inloggen, {"naam": self.naam, "wachtwoord": "mis"}, bron=self.bron)
        self.assertEqual(h.set_cookie, [])

    def test_de_rem_slaat_aan(self):
        for _ in range(6):
            _post(routes.inloggen, {"naam": self.naam, "wachtwoord": "mis"}, bron=self.bron)
        # Zelfs mét het juiste wachtwoord: de rem gaat vóór de controle, anders
        # is hij geen rem maar een vertraging.
        h = _post(routes.inloggen, {"naam": self.naam, "wachtwoord": "een goed wachtwoord"},
                  bron=self.bron)
        self.assertEqual(h.code, 429)
        self.assertGreater(h.payload.get("wacht", 0), 0)


class Gate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pid = store.maak_persoon("gate-" + os.urandom(4).hex(), "hash")

    def test_zonder_sessie_geen_toegang_ook_niet_voor_lezen(self):
        h = _Handler()
        self.assertIsNone(routes.gate(h, "/api/channels", schrijft=False))
        self.assertEqual(h.code, 401)

    def test_met_sessie_mag_lezen(self):
        token, _ = auth.start_sessie(self.pid)
        h = _Handler({"Cookie": "{}={}".format(auth.COOKIE, token)})
        self.assertIsNotNone(routes.gate(h, "/api/channels", schrijft=False))

    def test_schrijven_zonder_sessietoken_wordt_geweigerd(self):
        token, _ = auth.start_sessie(self.pid)
        h = _Handler({"Cookie": "{}={}".format(auth.COOKIE, token)})
        self.assertIsNone(routes.gate(h, "/api/send", schrijft=True))
        self.assertEqual(h.code, 403)

    def test_schrijven_met_sessietoken_mag(self):
        token, csrf = auth.start_sessie(self.pid)
        h = _Handler({"Cookie": "{}={}".format(auth.COOKIE, token),
                      auth.CSRF_HEADER: csrf})
        self.assertIsNotNone(routes.gate(h, "/api/send", schrijft=True))


class Uitnodigen(unittest.TestCase):
    def test_uitnodiging_werkt_een_keer(self):
        token = auth.nieuwe_uitnodiging("uitnodiging")
        naam = "gast-" + os.urandom(4).hex()
        eerste = _post(routes.uitnodiging_gebruiken,
                       {"token": token, "naam": naam, "wachtwoord": "lang genoeg hoor"})
        self.assertEqual(eerste.code, 201)
        tweede = _post(routes.uitnodiging_gebruiken,
                       {"token": token, "naam": naam + "2", "wachtwoord": "lang genoeg hoor"})
        self.assertEqual(tweede.code, 403)

    def test_kort_wachtwoord_wordt_geweigerd(self):
        token = auth.nieuwe_uitnodiging("uitnodiging")
        h = _post(routes.uitnodiging_gebruiken,
                  {"token": token, "naam": "kort", "wachtwoord": "kort"})
        self.assertEqual(h.code, 400)

    def test_setup_kan_niet_meer_als_er_iemand_is(self):
        store.maak_persoon("er-is-iemand-" + os.urandom(4).hex(), "hash")
        h = _post(routes.setup, {"token": "wat dan ook", "naam": "x", "wachtwoord": "y" * 12})
        self.assertEqual(h.code, 403)


if __name__ == "__main__":
    unittest.main()


class WachtwoordWijzigen(unittest.TestCase):
    """Je eigen wachtwoord, mét het huidige erbij: anders is een geleende
    sessie genoeg om iemand permanent buiten te sluiten."""

    def setUp(self):
        import auth_admin
        self.admin = auth_admin
        self.naam = "ww-" + os.urandom(4).hex()
        self.pid = store.maak_persoon(self.naam, auth.hash_wachtwoord("het oude wachtwoord"))
        self.token, self.csrf = auth.start_sessie(self.pid)
        self.sessie = auth.sessie_uit_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, self.token)})

    def _wijzig(self, huidig, nieuw):
        h = _Handler()
        self.admin.wachtwoord_wijzigen(h, self.sessie, {"huidig": huidig, "nieuw": nieuw})
        return h

    def test_zonder_het_huidige_wachtwoord_niet(self):
        h = self._wijzig("iets anders", "een nieuw lang wachtwoord")
        self.assertEqual(h.code, 403)
        self.assertTrue(auth.wachtwoord_klopt("het oude wachtwoord",
                                              store.persoon(self.pid)["hash"]))

    def test_te_kort_nieuw_wachtwoord_niet(self):
        h = self._wijzig("het oude wachtwoord", "kort")
        self.assertEqual(h.code, 400)

    def test_wijzigen_trekt_alle_sessies_in_en_geeft_een_nieuwe(self):
        tweede, _ = auth.start_sessie(self.pid)     # ander apparaat
        h = self._wijzig("het oude wachtwoord", "een nieuw lang wachtwoord")
        self.assertEqual(h.code, 200)
        self.assertTrue(auth.wachtwoord_klopt("een nieuw lang wachtwoord",
                                              store.persoon(self.pid)["hash"]))
        # het andere apparaat is eruit
        self.assertIsNone(auth.sessie_uit_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, tweede)}))
        # en dit apparaat kreeg een verse sessie mee
        self.assertTrue(h.set_cookie and auth.COOKIE in h.set_cookie[0])
        self.assertIn("csrf", h.payload)
