#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Een timer die faalt, faalt stil.

`check_units.py` vergelijkt geïnstalleerd met git. Dat zegt niets over of het
wérkt. Een systemd-timer blijft `active (waiting)` en plant netjes de volgende
run, ongeacht hoe de vorige afliep — van buiten ziet een dode taak er gezond uit.

Gemeten op 2026-09-16: `claude-secret-refresh.service` faalde 82 keer in veertien
dagen en slaagde nul keer, terwijl de timer al die tijd op `active (waiting)`
stond. De enige plek waar het stond was het journaal, en daar kijkt niemand
zonder reden.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_timers  # noqa: E402

LIJST = """NEXT                        LEFT  LAST  PASSED  UNIT                       ACTIVATES
Wed 2026-09-16 09:46:12 CEST 31min  n/a   n/a    claude-secret-refresh.timer claude-secret-refresh.service
Wed 2026-09-16 10:00:00 CEST 45min  n/a   n/a    ratatoskr-board.timer       ratatoskr-board.service
Wed 2026-09-16 06:00:00 CEST -      n/a   n/a    systemd-tmpfiles-clean.timer systemd-tmpfiles-clean.service
"""


class TestTimers(unittest.TestCase):
    def test_alleen_onze_eigen_timers(self):
        """Wat we niet beheren, hoeven we niet te bewaken — en een melding over
        een systemd-eigen timer is ruis die de gate onbruikbaar maakt."""
        self.assertEqual(check_timers.timers(LIJST),
                         ["claude-secret-refresh.timer", "ratatoskr-board.timer"])

    def test_lege_uitvoer_geeft_niets(self):
        self.assertEqual(check_timers.timers(""), [])


class TestToestand(unittest.TestCase):
    def test_leest_resultaat_en_exitcode(self):
        toon = "Result=exit-code\nExecMainStatus=255\nActiveEnterTimestamp=\n"
        service, resultaat, code = check_timers.toestand("x.timer", toon)
        self.assertEqual(service, "x.service")
        self.assertEqual((resultaat, code), ("exit-code", "255"))

    def test_ontbrekende_velden_worden_niet_geraden(self):
        service, resultaat, code = check_timers.toestand("x.timer", "")
        self.assertEqual((resultaat, code), ("?", "?"))


class TestFouten(unittest.TestCase):
    def test_geslaagd_is_geen_fout(self):
        self.assertEqual(check_timers.fouten([("a.service", "success", "0")]), [])

    def test_een_exitcode_is_een_fout(self):
        self.assertEqual(len(check_timers.fouten([("a.service", "exit-code", "255")])), 1)

    def test_success_met_niet_nul_telt_ook(self):
        """Result kan 'success' zeggen terwijl de laatste run niet-nul eindigde;
        dan is het geen succes."""
        self.assertEqual(len(check_timers.fouten([("a.service", "success", "1")])), 1)

    def test_onbekend_is_geen_bewijs_van_goed(self):
        """Niet kunnen vaststellen is iets anders dan vastgesteld hebben dat het
        goed ging. Stil doorlaten is precies hoe deze fout veertien dagen bleef
        liggen."""
        self.assertEqual(len(check_timers.fouten([("a.service", "?", "?")])), 1)


if __name__ == "__main__":
    unittest.main()
