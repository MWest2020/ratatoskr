#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""De tmux-kaarten: puur, zonder tmux en zonder klok.

Waarom deze bron bestaat: het bord toonde werksessies en PR's, maar niet de
tmux-sessies waarin het meeste werk feitelijk gebeurt. Wie niet aangekoppeld zat
zag niets, en dan moet Mark vragen wat er loopt — wat hij op 2026-09-14 deed.

Alles wat de kaart zégt is hier te testen zonder tmux te draaien; dat is dezelfde
scheiding als bij de andere bronnen (board_model puur, board_sources en
board_github halen op).
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_tmux  # noqa: E402

NU = 1_726_000_000.0


def regel(naam="werk", gemaakt=None, activiteit=None, aangekoppeld="0",
          pad="/home/agent/wordsworth", commando="claude"):
    gemaakt = NU - 3600 if gemaakt is None else gemaakt
    activiteit = NU - 600 if activiteit is None else activiteit
    return "\t".join([naam, str(gemaakt), str(activiteit), aangekoppeld,
                      pad, commando])


class TestProject(unittest.TestCase):
    def test_de_map_naam_is_het_project(self):
        self.assertEqual(board_tmux.project("/home/agent/wordsworth"),
                         ("wordsworth", False))

    def test_de_home_map_is_geen_project(self):
        """"agent" tonen is erger dan niets: het suggereert een project."""
        self.assertEqual(board_tmux.project("/home/agent", home="/home/agent"),
                         ("—", False))

    def test_een_verdwenen_werkmap_wordt_gemeld_niet_verstopt(self):
        naam, weg = board_tmux.project("/home/agent/rat-taal (deleted)")
        self.assertEqual(naam, "rat-taal")
        self.assertTrue(weg)


class TestParse(unittest.TestCase):
    def test_naam_project_en_activiteit(self):
        (k,) = board_tmux.parse([regel(naam="taal")], NU)
        self.assertEqual(k["title"], "taal")
        self.assertEqual(k["repo"], "wordsworth")
        self.assertEqual(k["id"], "tmux:taal")
        self.assertEqual(k["column"], "building")
        self.assertIn("claude", k["activity"])
        self.assertIn("min geleden", k["activity"])

    def test_aangekoppeld_is_zichtbaar(self):
        (aan,) = board_tmux.parse([regel(aangekoppeld="1")], NU)
        (uit,) = board_tmux.parse([regel(aangekoppeld="0")], NU)
        self.assertIn("aangekoppeld", aan["via"])
        self.assertNotIn("aangekoppeld", uit["via"])

    def test_verdwenen_werkmap_staat_in_de_activiteit(self):
        (k,) = board_tmux.parse([regel(pad="/home/agent/weg (deleted)")], NU)
        self.assertIn("werkmap bestaat niet meer", k["activity"])

    def test_een_onbekende_vorm_wordt_overgeslagen_niet_geraden(self):
        self.assertEqual(board_tmux.parse(["alleen-een-naam"], NU), [])
        self.assertEqual(board_tmux.parse([regel(gemaakt="geen-getal")], NU), [])

    def test_stil_na_laat_een_slapende_sessie_weg(self):
        oud = regel(activiteit=NU - 7200)
        self.assertEqual(board_tmux.parse([oud], NU, stil_na=3600), [])
        self.assertEqual(len(board_tmux.parse([oud], NU)), 1)  # standaard: blijft

    def test_leeftijd_komt_van_de_aanmaaktijd_niet_van_de_activiteit(self):
        (k,) = board_tmux.parse([regel(gemaakt=NU - 2 * 86400,
                                       activiteit=NU - 60)], NU)
        self.assertAlmostEqual(k["age_days"], 2.0, places=3)


class TestDuur(unittest.TestCase):
    def test_grenzen(self):
        self.assertEqual(board_tmux._duur(10), "zojuist")
        self.assertEqual(board_tmux._duur(600), "10 min geleden")
        self.assertEqual(board_tmux._duur(7200), "2 uur geleden")
        self.assertEqual(board_tmux._duur(3 * 86400), "3 dagen geleden")


class TestZonderTmux(unittest.TestCase):
    def test_geen_tmux_is_geen_fout(self):
        """Op een machine zonder sessies hoort het bord geen tmux-kaarten te
        tonen, niet een leesfout te melden."""
        self.assertEqual(board_tmux.tmux_cards(NU, listing=[]), [])


if __name__ == "__main__":
    unittest.main()


class TestBordKoppeling(unittest.TestCase):
    """De bron hangt aan de config, niet aan de machine.

    Dit is de enige bron die de host zelf ondervraagt in plaats van een pad uit
    de config te lezen. Stond hij ongevraagd aan, dan deed `build()` echte
    tmux-I/O in elke test — en dat brak meteen drie bestaande bordtests.
    """

    def setUp(self):
        import board
        self.board = board
        self.cfg = {"columns": [{"key": "building", "title": "bouwen",
                                 "stale_days": 3}],
                    "sources": {"openspec_glob": "/bestaat/niet/*",
                                "github_owner": "x", "session_runs": "/bestaat/niet",
                                "merged_days": 3,
                                "pr_cache": os.path.join(tempfile.mkdtemp(),
                                                         "prs.json"),
                                "pr_cache_seconds": 600}}
        import board_github
        self.oud = board_github.gh_json
        board_github.gh_json = lambda args: []
        self.addCleanup(lambda: setattr(board_github, "gh_json", self.oud))

    def test_zonder_config_geen_tmux_kaarten(self):
        snap = self.board.build(dict(self.cfg), now=NU)
        self.assertEqual([c for c in snap["cards"] if c["source"] == "tmux"], [])

    def test_met_config_aan_wordt_de_bron_bevraagd(self):
        cfg = {**self.cfg, "sources": {**self.cfg["sources"], "tmux": True}}
        geroepen = []
        oud = board_tmux.tmux_listing
        board_tmux.tmux_listing = lambda *a, **k: (geroepen.append(1), [regel()])[1]
        self.addCleanup(lambda: setattr(board_tmux, "tmux_listing", oud))
        snap = self.board.build(cfg, now=NU)
        self.assertTrue(geroepen)
        self.assertEqual(len([c for c in snap["cards"] if c["source"] == "tmux"]), 1)
