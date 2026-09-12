# SPDX-License-Identifier: EUPL-1.2
"""De terugval van RATATOSKR_ op BOOMHUIS_ is de enige weg terug na een
mislukte uitrol, dus die is getest en niet aangenomen."""
import os
import unittest

import settings


class Reading(unittest.TestCase):
    def setUp(self):
        for k in ("RATATOSKR_PROEF", "BOOMHUIS_PROEF"):
            os.environ.pop(k, None)

    tearDown = setUp

    def test_new_name(self):
        os.environ["RATATOSKR_PROEF"] = "nieuw"
        self.assertEqual(settings.read("PROEF"), "nieuw")

    def test_old_name_keeps_working(self):
        os.environ["BOOMHUIS_PROEF"] = "oud"
        self.assertEqual(settings.read("PROEF"), "oud")

    def test_new_wins(self):
        os.environ["BOOMHUIS_PROEF"] = "oud"
        os.environ["RATATOSKR_PROEF"] = "nieuw"
        self.assertEqual(settings.read("PROEF"), "nieuw")

    def test_empty_counts_as_absent(self):
        """Een per ongeluk lege regel in .env mag de terugval niet blokkeren."""
        os.environ["RATATOSKR_PROEF"] = ""
        os.environ["BOOMHUIS_PROEF"] = "oud"
        self.assertEqual(settings.read("PROEF"), "oud")

    def test_default(self):
        self.assertEqual(settings.read("PROEF", "vangnet"), "vangnet")

    def test_is_set(self):
        self.assertFalse(settings.is_set("PROEF"))
        os.environ["BOOMHUIS_PROEF"] = "x"
        self.assertTrue(settings.is_set("PROEF"))


if __name__ == "__main__":
    unittest.main()
