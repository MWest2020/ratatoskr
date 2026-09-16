#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""De gate moet beide kanten op kijken.

`check_units.py` vergeleek alleen repo → host: voor elke unit in de repo, staat
hij ook op de machine. Een unit die ALLEEN op de host bestaat was daarmee per
constructie onzichtbaar — de gate mat precies de verzameling waar het gat niet
in zat.

Gemeten op 2026-09-16: `claude-secret-refresh.{service,timer}` draaide hier al
maanden, stond nergens in git, en faalde 82 keer op rij zonder dat enige gate
iets zei.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_units  # noqa: E402


class TestHostUnits(unittest.TestCase):
    def setUp(self):
        self.map = tempfile.mkdtemp()

    def schrijf(self, naam):
        with open(os.path.join(self.map, naam), "w") as f:
            f.write("[Unit]\n")

    def test_alleen_wat_van_ons_is(self):
        """Wat wij niet beheren gaat ons niet aan; erover klagen maakt de gate
        ruis, en dan zet iemand hem uit."""
        for n in ("ratatoskr-x.service", "claude-y.timer", "docker.service",
                  "pipewire.socket"):
            self.schrijf(n)
        self.assertEqual(check_units.host_units(self.map),
                         ["claude-y.timer", "ratatoskr-x.service"])

    def test_een_map_die_niet_bestaat_is_geen_fout(self):
        self.assertEqual(check_units.host_units("/bestaat/niet"), [])


class TestAlleenOpDeHost(unittest.TestCase):
    def test_een_unit_die_nergens_in_git_staat_wordt_gemeld(self):
        uit = check_units.alleen_op_de_host({"ratatoskr-a.service"},
                                            ["ratatoskr-a.service",
                                             "claude-geheim.timer"], elders={})
        self.assertEqual(uit, [("claude-geheim.timer", None)])

    def test_een_uitzondering_draagt_zijn_reden(self):
        """Een kale allowlist zou hier ook werken en is slechter: over een half
        jaar weet niemand meer of een naam er nog hoort te staan."""
        uit = check_units.alleen_op_de_host(
            set(), ["zettelkast-daily.timer"],
            elders={"zettelkast-daily.timer": "hoort bij MWest2020/zettelkast"})
        (naam, reden), = uit
        self.assertEqual(naam, "zettelkast-daily.timer")
        self.assertIn("zettelkast", reden)

    def test_wat_in_git_staat_komt_er_niet_bij(self):
        self.assertEqual(
            check_units.alleen_op_de_host({"ratatoskr-a.service"},
                                          ["ratatoskr-a.service"], elders={}), [])

    def test_de_echte_uitzonderingslijst_heeft_overal_een_reden(self):
        """Een lege reden is een uitzondering die niets uitlegt — dan kun je de
        regel net zo goed weghalen."""
        for naam, reden in check_units.ELDERS.items():
            self.assertTrue(reden and reden.strip(), f"{naam} heeft geen reden")


if __name__ == "__main__":
    unittest.main()
