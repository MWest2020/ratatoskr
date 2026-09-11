# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor werksessies: marker, machtiging, grenzen, oogst.

Draaien: cd agents && python3 -m unittest test_sessies
Geen relay, geen claude — alles wat hier getest wordt is puur of gebruikt een
nep-proces, zodat dit in CI kan.
"""
import os
import tempfile
import time
import unittest

import prompts
import providers
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
        self.assertEqual(sessies.lees_marker("hoi\n!sessie zettelkast kijk naar de clips"),
                         ("zettelkast", "kijk naar de clips"))

    def test_zonder_opdracht(self):
        self.assertEqual(sessies.lees_marker("!sessie zettelkast"), ("zettelkast", ""))

    def test_alleen_de_eerste_telt(self):
        """Eén bericht zet hoogstens één sessie in gang."""
        t = "!sessie zettelkast een\n!sessie zettelkast twee"
        self.assertEqual(sessies.lees_marker(t)[1], "een")

    def test_geen_marker(self):
        self.assertIsNone(sessies.lees_marker("praat over !sessie in een zin"))

    def test_knippen_haalt_de_regel_weg(self):
        """Een geposte marker mag niet opnieuw gelezen kunnen worden."""
        uit = sessies.knip_marker("voor\n!sessie zettelkast doe iets\nna")
        self.assertNotIn("!sessie", uit)
        self.assertIn("voor", uit)
        self.assertIn("na", uit)

    def test_knippen_laat_de_tweede_staan_maar_start_niets(self):
        uit = sessies.knip_marker("!sessie zettelkast een\n!sessie zettelkast twee")
        self.assertEqual(sessies.lees_marker(uit), ("zettelkast", "twee"))


class Machtiging(unittest.TestCase):
    def test_onbekend_type_noemt_wat_er_wel_is(self):
        ok, reden = sessies.mag_starten(CFG, "nietbestaand", "odin", [])
        self.assertFalse(ok)
        self.assertIn("zettelkast", reden)

    def test_niet_gemachtigde_starter(self):
        ok, reden = sessies.mag_starten(CFG, "zettelkast", "roodteam", [])
        self.assertFalse(ok)
        self.assertIn("roodteam", reden)

    def test_onbekende_afzender_mag_niet(self):
        """PUB2NAME geeft '?' voor een onbekende pubkey — die staat nooit in starters."""
        self.assertFalse(sessies.mag_starten(CFG, "zettelkast", "?", [])[0])

    def test_een_sessie_per_starter(self):
        ok, reden = sessies.mag_starten(CFG, "zettelkast", "odin", [{"wie": "odin"}])
        self.assertFalse(ok)
        self.assertIn("al een sessie", reden)

    def test_globale_bovengrens(self):
        lopend = [{"wie": "mark"}, {"wie": "bouwer"}]
        ok, reden = sessies.mag_starten(CFG, "zettelkast", "odin", lopend)
        self.assertFalse(ok)
        self.assertIn("maximaal", reden)

    def test_mag_wel(self):
        self.assertEqual(sessies.mag_starten(CFG, "zettelkast", "odin", []), (True, ""))


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


class ExtraPaden(unittest.TestCase):
    """Een tweede leespad is een tweede vergunning, geen verruiming van de eerste."""

    def test_leespaden_krijgen_een_eigen_scope(self):
        uit = providers.scoped(["Read", "Grep", "WebFetch"], ["/data/bron/"])
        self.assertIn("Read(./**)", uit)
        self.assertIn("Read(/data/bron/**)", uit)
        self.assertNotIn("Read", uit)

    def test_schrijftools_krijgen_nooit_een_extra_pad(self):
        uit = providers.scoped(["Read", "Write"], ["/data/bron"])
        self.assertNotIn("Write(/data/bron/**)", uit)

    def test_zonder_extra_blijft_het_zoals_het_was(self):
        self.assertEqual(providers.scoped(["Read", "Bash"]), ["Read(./**)", "Bash"])


class Grenzen(unittest.TestCase):
    def test_verboden_tools_zijn_altijd_gedeny(self):
        for t in ("Write", "Edit", "Bash"):
            self.assertIn(t, sessies.VERBODEN)

    def test_ontbrekende_werkmap_start_niet(self):
        cfg = {"max_gelijktijdig": 2, "types": {"x": dict(CFG["types"]["zettelkast"],
                                                          werkmap="/bestaat/niet")}}
        with tempfile.TemporaryDirectory() as d:
            reg = sessies.Register(cfg, runs=d)
            s, reden = reg.start("x", "iets", "odin", "general", "cid")
        self.assertIsNone(s)
        self.assertIn("werkmap", reden)

    def test_laad_zonder_bestand_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sessies.laad(d).get("types"), {})

    def test_echte_sessies_yml_is_leesbaar_en_lezend(self):
        """De meegeleverde types mogen geen schrijfgereedschap declareren."""
        cfg = sessies.laad(os.path.dirname(os.path.abspath(__file__)))
        self.assertIn("zettelkast", cfg["types"])
        for naam, t in cfg["types"].items():
            self.assertTrue(t.get("starters"), naam)
            self.assertTrue(t.get("identiteit"), naam)
            for tool in t.get("tools") or []:
                self.assertNotIn(tool, sessies.VERBODEN, f"{naam} declareert {tool}")


class NepProc:
    """Genoeg proces om de oogst te testen zonder claude te draaien."""

    def __init__(self, rc=None):
        self.rc, self.pid, self.returncode = rc, os.getpid(), rc

    def poll(self):
        return self.rc


class Oogst(unittest.TestCase):
    def _sessie(self, regels, rc=0, max_s=60):
        d = tempfile.mkdtemp()
        pad = os.path.join(d, "run.jsonl")
        with open(pad, "w") as f:
            f.write("".join(regels))
        return {"typ": "zettelkast", "wie": "odin", "cid": "c", "cname": "general",
                "proc": NepProc(rc), "pad": pad, "uit": open(os.devnull, "w"),  # noqa: SIM115 (de Register sluit hem)
                "offset": 0, "t0": time.time(), "identiteit": "odin", "n": 0, "tp": 0.0,
                "max_s": max_s, "res": None}

    def _reg(self, s):
        reg = sessies.Register(CFG, runs=tempfile.mkdtemp())
        reg.lopend = [s]
        return reg

    def test_resultaat_wordt_gepost_met_voetregel(self):
        s = self._sessie(['{"type":"result","result":"gevonden: 1 clip",'
                          '"total_cost_usd":0.12,"num_turns":4}\n'])
        posts = []
        self._reg(s).tick(lambda x, t: posts.append(t))
        self.assertIn("gevonden: 1 clip", posts[-1])
        self.assertIn("$0.12", posts[-1])
        self.assertIn("4 beurten", posts[-1])

    def test_leeg_antwoord_meldt_dat_expliciet(self):
        """Stil niets posten leest als 'niets te melden' — dat is de false-clear."""
        s = self._sessie([])
        posts = []
        self._reg(s).tick(lambda x, t: posts.append(t))
        self.assertTrue(posts)
        self.assertIn("zonder antwoord", posts[-1])

    def test_halve_regel_wacht_op_de_volgende_tick(self):
        s = self._sessie(['{"type":"result","result":"af"}\n{"type":"resu'])
        reg = self._reg(s)
        posts = []
        reg.tick(lambda x, t: posts.append(t))
        self.assertIn("af", posts[-1])

    def test_voortgang_verschijnt_tussentijds(self):
        s = self._sessie(['{"type":"assistant","message":{"content":'
                          '[{"type":"tool_use","name":"Grep","input":{"pattern":"clip"}}]}}\n'],
                         rc=None)
        posts = []
        self._reg(s).tick(lambda x, t: posts.append(t))
        self.assertIn("Grep", posts[0])

    def test_budget_overschrijding_kapt_af(self):
        s = self._sessie([], rc=None, max_s=-1)   # negatief budget → meteen over
        posts = []
        reg = self._reg(s)
        reg._stop = lambda x: None                # niet echt onze eigen pid killen
        reg.tick(lambda x, t: posts.append(t))
        self.assertIn("afgekapt", posts[-1])
        self.assertEqual(reg.lopend, [])


if __name__ == "__main__":
    unittest.main()
