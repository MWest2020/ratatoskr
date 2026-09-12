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
import session_gate
import session_report
import sessies

CFG = {
    "max_gelijktijdig": 2,
    "types": {
        "zettelkast": {"werkmap": "/tmp", "starters": ["odin", "mark"],
                       "identiteit": "odin", "tools": ["Read"], "max_seconden": 60,
                       "prompt": "Opdracht: {opdracht}"},
    },
}


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
            s, reden = reg.start("x", "iets", "odin", "mark", "general", "cid")
        self.assertIsNone(s)
        self.assertIn("werkmap", reden)

    def test_laad_zonder_bestand_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sessies.laad(d).get("types"), {})

    def test_echte_sessies_yml_is_leesbaar(self):
        """Elk type declareert wie mag starten en onder wiens naam gepost wordt.
        Of het schrijfgereedschap mag hebben hangt af van `writes` — dat staat in
        de Schrijvend-tests hieronder."""
        cfg = sessies.laad(os.path.dirname(os.path.abspath(__file__)))
        self.assertIn("zettelkast", cfg["types"])
        for naam, t in cfg["types"].items():
            self.assertTrue(t.get("starters"), naam)
            self.assertTrue(t.get("identiteit"), naam)


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
        return {"typ": "zettelkast", "starter": "odin", "requester": "mark",
                "cid": "c", "cname": "general",
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

class Schrijvend(unittest.TestCase):
    """Een schrijvend type krijgt meer, een lezend type krijgt dat nooit."""

    def test_reading_type_never_gets_write_tools(self):
        cfg = sessies.laad(os.path.dirname(os.path.abspath(__file__)))
        for naam, t in cfg["types"].items():
            if t.get("writes"):
                continue
            for tool in t.get("tools") or []:
                self.assertNotIn(tool, sessies.VERBODEN, f"{naam} declareert {tool}")

    def test_writing_type_still_never_gets_task_or_killshell(self):
        """Task spawnt agents buiten elk zicht; KillShell raakt vreemde processen."""
        cfg = sessies.laad(os.path.dirname(os.path.abspath(__file__)))
        for naam, t in cfg["types"].items():
            for tool in t.get("tools") or []:
                self.assertNotIn(tool, sessies.VERBODEN_ALTIJD, f"{naam} declareert {tool}")

    def test_build_type_is_declared_writing_and_narrowly_started(self):
        cfg = sessies.laad(os.path.dirname(os.path.abspath(__file__)))
        build = cfg["types"]["build"]
        self.assertTrue(build["writes"])
        # Het recht om te lezen geeft geen recht om te bouwen.
        self.assertNotIn("odin", build["starters"])




if __name__ == "__main__":
    unittest.main()
