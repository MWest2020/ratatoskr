# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor de POORT van een werksessie: marker, machtiging, clausule.

De runner (register, oogst, grenzen, rapport) staat in test_sessies.py. Die
splitsing volgt de code: session_gate.py is puur, sessies.py raakt processen aan.

Draaien: cd agents && python3 -m unittest test_session_gate
"""
import os
import tempfile
import unittest

import prompts
import session_gate
import sessies


CFG = {
    "max_gelijktijdig": 2,
    "types": {
        "zettelkast": {"werkmap": "/tmp", "starters": ["odin", "mark"],
                       "identiteit": "odin", "tools": ["Read"], "max_seconden": 60,
                       "prompt": "Opdracht: {opdracht}"},
    },
}


class Marker(unittest.TestCase):
    def test_leest_type_en_opdracht(self):
        self.assertEqual(session_gate.read_marker("hoi\n!sessie zettelkast kijk naar de clips"),
                         ("zettelkast", "kijk naar de clips"))

    def test_zonder_opdracht(self):
        self.assertEqual(session_gate.read_marker("!sessie zettelkast"), ("zettelkast", ""))

    def test_alleen_de_eerste_telt(self):
        """Eén bericht zet hoogstens één sessie in gang."""
        t = "!sessie zettelkast een\n!sessie zettelkast twee"
        self.assertEqual(session_gate.read_marker(t)[1], "een")

    def test_geen_marker(self):
        self.assertIsNone(session_gate.read_marker("praat over !sessie in een zin"))

    def test_knippen_haalt_de_regel_weg(self):
        """Een geposte marker mag niet opnieuw gelezen kunnen worden."""
        uit = session_gate.strip_marker("voor\n!sessie zettelkast doe iets\nna")
        self.assertNotIn("!sessie", uit)
        self.assertIn("voor", uit)
        self.assertIn("na", uit)

    def test_knippen_laat_de_tweede_staan_maar_start_niets(self):
        uit = session_gate.strip_marker("!sessie zettelkast een\n!sessie zettelkast twee")
        self.assertEqual(session_gate.read_marker(uit), ("zettelkast", "twee"))

class Machtiging(unittest.TestCase):
    def mag(self, typ="zettelkast", starter="odin", requester="mark", lopend=()):
        return session_gate.may_start(CFG, typ, starter, requester, list(lopend))

    def test_onbekend_type_noemt_wat_er_wel_is(self):
        ok, reden = self.mag(typ="nietbestaand")
        self.assertFalse(ok)
        self.assertIn("zettelkast", reden)

    def test_niet_gemachtigde_starter(self):
        ok, reden = self.mag(starter="roodteam")
        self.assertFalse(ok)
        self.assertIn("roodteam", reden)

    def test_agent_namens_iemand_die_niet_mag(self):
        """Odin mag starten, maar niet namens wie zelf niet op starters staat."""
        ok, reden = self.mag(requester="roodteam")
        self.assertFalse(ok)
        self.assertIn("namens", reden)

    def test_onbekende_afzender_mag_niet(self):
        """PUB2NAME geeft '?' voor een onbekende pubkey — die staat nooit in starters."""
        self.assertFalse(self.mag(starter="?", requester="?")[0])

    def test_een_sessie_per_requester(self):
        """De limiet gaat per vrager: twee mensen via odin mag wél."""
        ok, reden = self.mag(lopend=[{"requester": "mark"}])
        self.assertFalse(ok)
        self.assertIn("al een sessie", reden)

    def test_tweede_persoon_via_dezelfde_agent_mag(self):
        ok, reden = self.mag(requester="odin", lopend=[{"requester": "mark"}])
        self.assertTrue(ok, reden)

    def test_globale_bovengrens(self):
        lopend = [{"requester": "x"}, {"requester": "y"}]
        ok, reden = self.mag(lopend=lopend)
        self.assertFalse(ok)
        self.assertIn("maximaal", reden)

    def test_mag_wel(self):
        self.assertEqual(self.mag(), (True, ""))

class Clausule(unittest.TestCase):
    """Een agent die geen starter is, hoort niet te lezen dat hij sessies kan starten."""

    def test_starter_krijgt_de_types(self):
        t = prompts.sessie_clausule(CFG, "odin")
        self.assertIn("!sessie", t)
        self.assertIn("zettelkast", t)

    def test_niet_starter_krijgt_niets(self):
        self.assertEqual(prompts.sessie_clausule(CFG, "roodteam"), "")

    def test_geen_types_geen_clausule(self):
        self.assertEqual(prompts.sessie_clausule({"types": {}}, "odin"), "")

class EenListener(unittest.TestCase):
    """Twee listeners = elk bericht dubbel beantwoord en elke sessie dubbel
    gestart. Gemeten 2026-09-11 in #architectuur: één marker, twee sessies."""

    def test_tweede_instantie_krijgt_niets(self):
        import bootstrap
        pad = os.path.join(tempfile.mkdtemp(), "slot")
        eerste = bootstrap.alleen_ik(pad)
        self.assertIsNotNone(eerste)
        self.assertIsNone(bootstrap.alleen_ik(pad))
        eerste.close()                      # slot vrij
        tweede = bootstrap.alleen_ik(pad)
        self.assertIsNotNone(tweede)
        tweede.close()


if __name__ == "__main__":
    unittest.main()
