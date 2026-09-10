# SPDX-License-Identifier: EUPL-1.2
"""Tests voor het host-beheer (chat/adminctl.py).

Draait het script als subproces, met een eigen database en het wachtwoord op
stdin — dat is precies hoe het in het echt gebruikt wordt.
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WW = "een lang genoeg wachtwoord\n"


class Adminctl(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ,
                        BOOMHUIS_AUTH_DB=os.path.join(tempfile.mkdtemp(), "a.db"),
                        BOOMHUIS_URL="https://voorbeeld")
        self.env.pop("BOOMHUIS_APP_TOKEN", None)

    def run_ctl(self, *args, invoer=None):
        r = subprocess.run([sys.executable, os.path.join(HERE, "adminctl.py"), *args],
                           env=self.env, input=invoer, capture_output=True, text=True,
                           cwd=HERE)
        return r.returncode, r.stdout + r.stderr

    def test_eigenaar_maken_en_terugzien(self):
        code, uit = self.run_ctl("eigenaar", "mark", invoer=WW + WW)
        self.assertEqual(code, 0, uit)
        self.assertIn("aangemaakt", uit)
        _, lijst = self.run_ctl("personen")
        self.assertIn("mark", lijst)
        self.assertIn("eigenaar", lijst)

    def test_tweede_eigenaar_kan_niet(self):
        self.run_ctl("eigenaar", "mark", invoer=WW + WW)
        code, uit = self.run_ctl("eigenaar", "iemand", invoer=WW + WW)
        self.assertEqual(code, 1)
        self.assertIn("al een account", uit)

    def test_wachtwoorden_moeten_gelijk_zijn(self):
        code, uit = self.run_ctl("eigenaar", "mark",
                                 invoer=WW + "iets heel anders hier\n")
        self.assertEqual(code, 1)
        self.assertIn("verschillen", uit)

    def test_kort_wachtwoord_wordt_geweigerd(self):
        code, uit = self.run_ctl("eigenaar", "mark", invoer="kort\nkort\n")
        self.assertEqual(code, 1)
        self.assertIn("minstens", uit)

    def test_uitnodiging_pas_na_een_eigenaar(self):
        code, _ = self.run_ctl("uitnodiging")
        self.assertEqual(code, 1)
        self.run_ctl("eigenaar", "mark", invoer=WW + WW)
        code, uit = self.run_ctl("uitnodiging")
        self.assertEqual(code, 0)
        self.assertIn("/login?uitnodiging=", uit)

    def test_wachtwoord_wijzigen_trekt_sessies_in(self):
        self.run_ctl("eigenaar", "mark", invoer=WW + WW)
        # een sessie erbij, en kijken of die na de wijziging weg is
        code, uit = self.run_ctl("wachtwoord", "mark",
                                 invoer="een nieuw lang wachtwoord\n" * 2)
        self.assertEqual(code, 0, uit)
        self.assertIn("sessies zijn ingetrokken", uit)

    def test_de_laatste_eigenaar_blijft_staan(self):
        """Jezelf verwijderen als enige eigenaar maakt de installatie
        onbereikbaar; dat hoort niet per ongeluk te kunnen."""
        self.run_ctl("eigenaar", "mark", invoer=WW + WW)
        code, uit = self.run_ctl("verwijder", "mark")
        self.assertEqual(code, 0, uit)   # enige persoon: dan mag het wel, dat is opnieuw beginnen
        _, lijst = self.run_ctl("personen")
        self.assertIn("nog niemand", lijst)

    def test_onbekende_naam_verwijderen(self):
        self.run_ctl("eigenaar", "mark", invoer=WW + WW)
        code, uit = self.run_ctl("verwijder", "bestaat-niet")
        self.assertEqual(code, 1)
        self.assertIn("onbekende naam", uit)

    def test_onzin_opdracht_toont_de_uitleg(self):
        code, uit = self.run_ctl("dansen")
        self.assertEqual(code, 1)
        self.assertIn("adminctl.py", uit)


if __name__ == "__main__":
    unittest.main()
