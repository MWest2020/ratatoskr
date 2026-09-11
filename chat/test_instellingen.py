# SPDX-License-Identifier: EUPL-1.2
"""De terugval van RATATOSKR_ op BOOMHUIS_ is de enige weg terug na een
mislukte uitrol, dus die is getest en niet aangenomen."""
import os
import unittest

import instellingen


class Lezen(unittest.TestCase):
    def setUp(self):
        for k in ("RATATOSKR_PROEF", "BOOMHUIS_PROEF"):
            os.environ.pop(k, None)

    tearDown = setUp

    def test_nieuwe_naam(self):
        os.environ["RATATOSKR_PROEF"] = "nieuw"
        self.assertEqual(instellingen.lees("PROEF"), "nieuw")

    def test_oude_naam_blijft_werken(self):
        os.environ["BOOMHUIS_PROEF"] = "oud"
        self.assertEqual(instellingen.lees("PROEF"), "oud")

    def test_nieuwe_wint(self):
        os.environ["BOOMHUIS_PROEF"] = "oud"
        os.environ["RATATOSKR_PROEF"] = "nieuw"
        self.assertEqual(instellingen.lees("PROEF"), "nieuw")

    def test_leeg_telt_als_afwezig(self):
        """Een per ongeluk lege regel in .env mag de terugval niet blokkeren."""
        os.environ["RATATOSKR_PROEF"] = ""
        os.environ["BOOMHUIS_PROEF"] = "oud"
        self.assertEqual(instellingen.lees("PROEF"), "oud")

    def test_default(self):
        self.assertEqual(instellingen.lees("PROEF", "vangnet"), "vangnet")

    def test_gezet(self):
        self.assertFalse(instellingen.gezet("PROEF"))
        os.environ["BOOMHUIS_PROEF"] = "x"
        self.assertTrue(instellingen.gezet("PROEF"))


if __name__ == "__main__":
    unittest.main()
