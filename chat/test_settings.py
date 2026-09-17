# SPDX-License-Identifier: MIT
"""The fallback from RATATOSKR_ to BOOMHUIS_ is the only way back after a failed
rollout, so it is tested and not assumed."""
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
        """An accidentally empty line in .env must not block the fallback."""
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
