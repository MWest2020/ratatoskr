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


class Wachtwoorden(unittest.TestCase):
    def test_klopt_en_klopt_niet(self):
        h = auth.hash_wachtwoord("een lang genoeg wachtwoord", n=2 ** 12)
        self.assertTrue(auth.wachtwoord_klopt("een lang genoeg wachtwoord", h))
        self.assertFalse(auth.wachtwoord_klopt("iets anders", h))

    def test_zelfde_wachtwoord_geeft_andere_hash(self):
        """Elk account zijn eigen salt, anders verraden gelijke hashes gelijke
        wachtwoorden."""
        a = auth.hash_wachtwoord("hetzelfde wachtwoord", n=2 ** 12)
        b = auth.hash_wachtwoord("hetzelfde wachtwoord", n=2 ** 12)
        self.assertNotEqual(a, b)

    def test_lichtere_parameters_heten_verouderd(self):
        self.assertTrue(auth.verouderd(auth.hash_wachtwoord("x" * 12, n=2 ** 12)))
        self.assertFalse(auth.verouderd(auth.hash_wachtwoord("x" * 12)))

    def test_de_ingestelde_parameters_draaien_echt(self):
        """scrypt weigert boven OpenSSL's geheugengrens (32 MB) met "memory
        limit exceeded". Met N=2**15 gebeurde dat precies — dat merk je pas bij
        de eerste echte login, dus staat het hier."""
        h = auth.hash_wachtwoord("een wachtwoord van genoeg tekens")
        self.assertTrue(auth.wachtwoord_klopt("een wachtwoord van genoeg tekens", h))

    def test_kapotte_hash_geeft_geen_toegang(self):
        for rommel in ("", "geen$hash", "argon2$1$2$3$4$5", None):
            self.assertFalse(auth.wachtwoord_klopt("wat dan ook", rommel))


class TweedeFactor(unittest.TestCase):
    def test_code_klopt_binnen_speling(self):
        geheim = auth.nieuw_totp_geheim()
        nu = time.time()
        code = auth._totp(geheim, int(nu // 30))
        self.assertTrue(auth.totp_klopt(geheim, code, nu=nu)[0])

    def test_code_is_niet_twee_keer_bruikbaar(self):
        geheim = auth.nieuw_totp_geheim()
        nu = time.time()
        code = auth._totp(geheim, int(nu // 30))
        ok, teller = auth.totp_klopt(geheim, code, nu=nu)
        self.assertTrue(ok)
        self.assertFalse(auth.totp_klopt(geheim, code, laatste=teller, nu=nu)[0])

    def test_onzin_wordt_geweigerd(self):
        geheim = auth.nieuw_totp_geheim()
        for code in ("", "abcdef", "12345", None):
            self.assertFalse(auth.totp_klopt(geheim, code)[0])


class Sessies(unittest.TestCase):
    def setUp(self):
        self.pid = store.maak_persoon("sessietest-" + os.urandom(4).hex(), "hash")

    def test_sessie_leeft_en_is_in_te_trekken(self):
        token, csrf = auth.start_sessie(self.pid)
        koppen = {"Cookie": "{}={}".format(auth.COOKIE, token)}
        self.assertIsNotNone(auth.sessie_uit_cookie(koppen))
        auth.stop_sessie(koppen)
        self.assertIsNone(auth.sessie_uit_cookie(koppen))
        self.assertTrue(csrf)

    def test_verlopen_sessie_telt_niet(self):
        token, _ = auth.start_sessie(self.pid)
        store.maak_sessie(auth._hash(token), self.pid, "x", store.nu() - 1)
        koppen = {"Cookie": "{}={}".format(auth.COOKIE, token)}
        self.assertIsNone(auth.sessie_uit_cookie(koppen))

    def test_overal_uitloggen_raakt_alle_apparaten(self):
        een, _ = auth.start_sessie(self.pid)
        twee, _ = auth.start_sessie(self.pid)
        auth.stop_sessie({"Cookie": "{}={}".format(auth.COOKIE, een)}, overal=True)
        self.assertIsNone(auth.sessie_uit_cookie(
            {"Cookie": "{}={}".format(auth.COOKIE, twee)}))

    def test_alleen_de_hash_staat_in_de_database(self):
        """Wie het bestand leest heeft daar geen bruikbare sessie aan."""
        token, _ = auth.start_sessie(self.pid)
        with store._verbind() as con:
            rijen = [r["hash"] for r in con.execute("SELECT hash FROM sessies")]
        self.assertNotIn(token, rijen)
        self.assertIn(auth._hash(token), rijen)

    def test_csrf_moet_kloppen(self):
        token, csrf = auth.start_sessie(self.pid)
        sessie = auth.sessie_uit_cookie({"Cookie": "{}={}".format(auth.COOKIE, token)})
        self.assertTrue(auth.csrf_klopt({auth.CSRF_HEADER: csrf}, sessie))
        self.assertFalse(auth.csrf_klopt({auth.CSRF_HEADER: "iets anders"}, sessie))
        self.assertFalse(auth.csrf_klopt({}, sessie))


class Cookie(unittest.TestCase):
    def test_secure_buiten_localhost(self):
        self.assertIn("Secure", auth.cookie_kop("t", "boomhuis-relay.tail8f7877.ts.net"))
        self.assertNotIn("Secure", auth.cookie_kop("t", "localhost:8090"))

    def test_altijd_httponly_en_samesite(self):
        kop = auth.cookie_kop("t", "localhost")
        self.assertIn("HttpOnly", kop)
        self.assertIn("SameSite=Lax", kop)


class Uitnodigingen(unittest.TestCase):
    def test_werkt_precies_een_keer(self):
        token = auth.nieuwe_uitnodiging("uitnodiging")
        self.assertTrue(auth.uitnodiging_geldig(token, "uitnodiging"))
        self.assertTrue(auth.gebruik_uitnodiging(token))
        self.assertFalse(auth.gebruik_uitnodiging(token))
        self.assertFalse(auth.uitnodiging_geldig(token, "uitnodiging"))

    def test_soort_moet_kloppen(self):
        """Een setup-link is geen uitnodiging: anders maakt de tweede persoon
        zichzelf eigenaar."""
        token = auth.nieuwe_uitnodiging("setup")
        self.assertFalse(auth.uitnodiging_geldig(token, "uitnodiging"))

    def test_verlopen_uitnodiging_geldt_niet(self):
        token = auth.nieuwe_uitnodiging("uitnodiging")
        store.maak_uitnodiging(auth._hash(token), "uitnodiging", store.nu() - 1)
        self.assertFalse(auth.uitnodiging_geldig(token, "uitnodiging"))


class OudeToken(unittest.TestCase):
    """Het migratiepad: zolang er niemand is mag het oude gedeelde token de
    eigenaar aanmaken. Zodra er iemand is, nooit meer."""

    def setUp(self):
        self._oud = os.environ.get("BOOMHUIS_APP_TOKEN")
        os.environ["BOOMHUIS_APP_TOKEN"] = "oud-gedeeld-token"

    def tearDown(self):
        if self._oud is None:
            os.environ.pop("BOOMHUIS_APP_TOKEN", None)
        else:
            os.environ["BOOMHUIS_APP_TOKEN"] = self._oud

    def test_niet_meer_zodra_er_iemand_is(self):
        store.maak_persoon("iemand-" + os.urandom(4).hex(), "hash")
        self.assertFalse(auth.setup_token_geldig("oud-gedeeld-token"))


if __name__ == "__main__":
    unittest.main()
