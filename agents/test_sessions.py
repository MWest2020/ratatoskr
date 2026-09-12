# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor werksessies: marker, machtiging, grenzen, oogst.

Draaien: cd agents && python3 -m unittest test_sessions
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
import sessions

CFG = {
    "max_concurrent": 2,
    "types": {
        "zettelkast": {"workdir": "/tmp", "starters": ["odin", "mark"],
                       "identity": "odin", "tools": ["Read"], "max_seconds": 60,
                       "prompt": "Opdracht: {task}"},
    },
}


class ExtraPaths(unittest.TestCase):
    """Een tweede leespad is een tweede vergunning, geen verruiming van de eerste."""

    def test_read_paths_get_their_own_scope(self):
        out = providers.scoped(["Read", "Grep", "WebFetch"], ["/data/bron/"])
        self.assertIn("Read(./**)", out)
        self.assertIn("Read(/data/bron/**)", out)
        self.assertNotIn("Read", out)

    def test_write_tools_never_get_an_extra_path(self):
        out = providers.scoped(["Read", "Write"], ["/data/bron"])
        self.assertNotIn("Write(/data/bron/**)", out)

    def test_without_extra_it_stays_as_it_was(self):
        self.assertEqual(providers.scoped(["Read", "Bash"]), ["Read(./**)", "Bash"])

class Limits(unittest.TestCase):
    def test_forbidden_tools_are_always_denied(self):
        for t in ("Write", "Edit", "Bash"):
            self.assertIn(t, sessions.FORBIDDEN)

    def test_missing_workdir_does_not_start(self):
        cfg = {"max_concurrent": 2, "types": {"x": dict(CFG["types"]["zettelkast"],
                                                       workdir="/bestaat/niet")}}
        with tempfile.TemporaryDirectory() as d:
            reg = sessions.Register(cfg, runs=d)
            s, reason = reg.start("x", "iets", "odin", "mark", "general", "cid")
        self.assertIsNone(s)
        self.assertIn("werkmap", reason)

    def test_load_without_file_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sessions.load(d).get("types"), {})

    def test_real_sessions_yml_is_readable(self):
        """Elk type declareert wie mag starten en onder wiens naam gepost wordt.
        Of het schrijfgereedschap mag hebben hangt af van `writes` — dat staat in
        de Writing-tests hieronder."""
        cfg = sessions.load(os.path.dirname(os.path.abspath(__file__)))
        self.assertIn("zettelkast", cfg["types"])
        for name, t in cfg["types"].items():
            self.assertTrue(t.get("starters"), name)
            self.assertTrue(t.get("identity"), name)


class FakeProc:
    """Genoeg proces om de oogst te testen zonder claude te draaien."""

    def __init__(self, rc=None):
        self.rc, self.pid, self.returncode = rc, os.getpid(), rc

    def poll(self):
        return self.rc

class Harvest(unittest.TestCase):
    def _session(self, lines, rc=0, max_s=60):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "run.jsonl")
        with open(path, "w") as f:
            f.write("".join(lines))
        return {"type": "zettelkast", "starter": "odin", "requester": "mark",
                "cid": "c", "cname": "general",
                "proc": FakeProc(rc), "path": path, "out": open(os.devnull, "w"),  # noqa: SIM115 (de Register sluit hem)
                "offset": 0, "t0": time.time(), "identity": "odin", "n": 0, "tp": 0.0,
                "max_s": max_s, "res": None}

    def _reg(self, s):
        reg = sessions.Register(CFG, runs=tempfile.mkdtemp())
        reg.running = [s]
        return reg

    def test_result_is_posted_with_a_footer(self):
        s = self._session(['{"type":"result","result":"gevonden: 1 clip",'
                          '"total_cost_usd":0.12,"num_turns":4}\n'])
        posts = []
        self._reg(s).tick(lambda x, t: posts.append(t))
        self.assertIn("gevonden: 1 clip", posts[-1])
        self.assertIn("$0.12", posts[-1])
        self.assertIn("4 beurten", posts[-1])

    def test_empty_answer_says_so_explicitly(self):
        """Stil niets posten leest als 'niets te melden' — dat is de false-clear."""
        s = self._session([])
        posts = []
        self._reg(s).tick(lambda x, t: posts.append(t))
        self.assertTrue(posts)
        self.assertIn("zonder antwoord", posts[-1])

    def test_half_a_line_waits_for_the_next_tick(self):
        s = self._session(['{"type":"result","result":"af"}\n{"type":"resu'])
        reg = self._reg(s)
        posts = []
        reg.tick(lambda x, t: posts.append(t))
        self.assertIn("af", posts[-1])

    def test_progress_appears_along_the_way(self):
        s = self._session(['{"type":"assistant","message":{"content":'
                          '[{"type":"tool_use","name":"Grep","input":{"pattern":"clip"}}]}}\n'],
                         rc=None)
        posts = []
        self._reg(s).tick(lambda x, t: posts.append(t))
        self.assertIn("Grep", posts[0])

    def test_exceeding_the_budget_cuts_off(self):
        s = self._session([], rc=None, max_s=-1)   # negatief budget → meteen over
        posts = []
        reg = self._reg(s)
        reg._stop = lambda x: None                # niet echt onze eigen pid killen
        reg.tick(lambda x, t: posts.append(t))
        self.assertIn("afgekapt", posts[-1])
        self.assertEqual(reg.running, [])


if __name__ == "__main__":
    unittest.main()

class Writing(unittest.TestCase):
    """Een schrijvend type krijgt meer, een lezend type krijgt dat nooit."""

    def test_reading_type_never_gets_write_tools(self):
        cfg = sessions.load(os.path.dirname(os.path.abspath(__file__)))
        for name, t in cfg["types"].items():
            if t.get("writes"):
                continue
            for tool in t.get("tools") or []:
                self.assertNotIn(tool, sessions.FORBIDDEN, f"{name} declareert {tool}")

    def test_writing_type_still_never_gets_task_or_killshell(self):
        """Task spawnt agents buiten elk zicht; KillShell raakt vreemde processen."""
        cfg = sessions.load(os.path.dirname(os.path.abspath(__file__)))
        for name, t in cfg["types"].items():
            for tool in t.get("tools") or []:
                self.assertNotIn(tool, sessions.ALWAYS_FORBIDDEN, f"{name} declareert {tool}")

    def test_build_type_is_declared_writing_and_narrowly_started(self):
        cfg = sessions.load(os.path.dirname(os.path.abspath(__file__)))
        build = cfg["types"]["build"]
        self.assertTrue(build["writes"])
        # Het recht om te lezen geeft geen recht om te bouwen.
        self.assertNotIn("odin", build["starters"])




if __name__ == "__main__":
    unittest.main()
