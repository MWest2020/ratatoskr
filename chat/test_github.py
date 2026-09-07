# SPDX-License-Identifier: EUPL-1.2
"""Invoervalidatie van de GitHub-leeslaag.

Waarom dit bestaat: `/api/prs?repo=boomhuis` (zonder owner) ging ongecontroleerd
door naar de GitHub-API en kwam terug als een **502 met rauwe upstream-tekst**.
Een invoerfout die zich voordoet als een storing, en de gebruiker ziet
"HTTP Error 404: Not Found" in plaats van "verwacht owner/naam".
"""
import unittest

import github


class ValidRepoTest(unittest.TestCase):
    def test_owner_slash_naam_is_geldig(self):
        for naam in ("MWest2020/boomhuis", "a/b", "MWest2020/internetnl-cli",
                     "MWest2020/Road_to_el_DORA-do", "org.io/repo.js"):
            self.assertTrue(github.valid_repo(naam), naam)

    def test_zonder_owner_is_ongeldig(self):
        self.assertFalse(github.valid_repo("boomhuis"))

    def test_padtekens_komen_er_niet_door(self):
        # Elk segment moet met een alfanumeriek teken beginnen, anders glippen
        # ".." en "." erdoor en gaat een pad-achtige waarde de URL in.
        for naam in ("../x", "./x", "a/..", "a/../b", "a/b/c", "/x", "x/"):
            self.assertFalse(github.valid_repo(naam), naam)

    def test_leeg_en_witruimte_zijn_ongeldig(self):
        for naam in ("", None, "a b/c", "a/b c", " a/b"):
            self.assertFalse(github.valid_repo(naam), repr(naam))

    def test_lengte_is_begrensd(self):
        self.assertFalse(github.valid_repo("a" * 200 + "/b"))


if __name__ == "__main__":
    unittest.main()
