# SPDX-License-Identifier: MIT
"""The build road (odin-runs-the-factory phase 1), offline: which markers count,
which builds may start, what a chain's output means, and that every event lands
on the issue. GitHub, Kubernetes and the chain itself are faked."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

import build
import build_runner
import build_wiring

CHAIN_LOG = """=== keten: rol architect ===
[dispatch] branch=habitat/architect/x-1
[dispatch] 3 artefact(en) -> {store}
keten: architect -> habitat/architect/x-1
=== keten: rol builder ===
[dispatch] branch=habitat/builder/x-2
keten: rol builder niet geslaagd (dispatch exit 1) — branch habitat/builder/x-2 — keten gestopt
"""


def cfg(tmp, **kw):
    c = {"owner": "MWest2020", "repos": ["ratatoskr", "Wanderer"], "builds_per_day": 2,
         "max_concurrent": 1, "habitat_dir": tmp, "worker_image": "img:abcdef123456789",
         "kubectl": "ssh jumpy kubectl", "logdir": tmp, "runs": os.path.join(tmp, "runs")}
    c.update(kw)
    return c


def gh(code=0):
    return lambda argv, **kw: subprocess.CompletedProcess(argv, code, "3", "")


class Marker(unittest.TestCase):
    def test_first_line_only_for_an_agent(self):
        self.assertEqual(build.read_marker("!build ratatoskr some-change\nok"),
                         ("ratatoskr", "some-change", 0))
        self.assertIsNone(build.read_marker("a quote:\n!build ratatoskr some-change"))

    def test_anywhere_for_mark_and_with_an_issue(self):
        self.assertEqual(build.read_marker("go\n!build Wanderer fix-x #42", own=False),
                         ("Wanderer", "fix-x", 42))

    def test_crafted_names_are_not_a_marker(self):
        for bad in ("!build ../x c", "!build r c; rm -rf /", "!build r $(id)"):
            self.assertIsNone(build.read_marker(bad, own=False), bad)


class Check(unittest.TestCase):
    def test_the_gates(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(t)
            self.assertEqual(build.check(c, "wanderer", "x", [], gh()), ("Wanderer", ""))
            self.assertIn("not on the factory's list", build.check(c, "alma", "x", [], gh())[1])
            self.assertIn("still running", build.check(c, "ratatoskr", "x", [1], gh())[1])
            self.assertIn("no OpenSpec change", build.check(c, "ratatoskr", "x", [], gh(1))[1])

    def test_the_daily_budget(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(t, builds_per_day=1)
            os.makedirs(c["runs"])
            with open(os.path.join(c["runs"], "a.log"), "w") as fh:
                fh.write(json.dumps({"started": 1_800_000_000}) + "\n")
            why = build.check(c, "ratatoskr", "x", [], gh(), now=lambda: 1_800_000_100)[1]
            self.assertIn("budget", why)


class Chain(unittest.TestCase):
    def test_events_from_the_chain_output(self):
        with tempfile.TemporaryDirectory() as store:
            json.dump({"verdict": "ok", "num_turns": 12, "total_cost_usd": 0.4},
                      open(os.path.join(store, "run-report.json"), "w"))
            evs = build_runner.events(CHAIN_LOG.format(store=store).splitlines())
            self.assertEqual([(k, r) for k, r, _ in evs], [("passed", "architect"),
                                                           ("failed", "builder")])
            c = build_runner.comment(*evs[0])
            self.assertIn("architect: PASS", c)
            self.assertIn("verdict ok", c)
            self.assertIn("builder: FAIL", build_runner.comment(*evs[1]))


class FakeProc:
    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


class Wiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.said, self.calls, self.argv = [], [], []
        c = cfg(self.tmp.name)

        class Issues:
            def create(s, repo, title, body, labels):
                self.calls.append(("create", repo, title, labels))
                return 7, "u", ""

            def comment(s, repo, n, body):
                self.calls.append(("comment", repo, n, body))
                return ""

        def popen(argv, **kw):
            self.argv.append((argv, kw["env"]["KUBECTL"], kw["env"]["CLAUDE_CREDS_FILE"]))
            kw["stdout"].write(CHAIN_LOG.format(store="/nowhere"))
            kw["stdout"].flush()
            return FakeProc(code=1)
        self.builds = build_runner.Builds(c, popen=popen)
        agents = {"odin": {"nsec": "n", "npub": "np"}}
        self.try_build, self.tick = build_wiring.setup(
            c, agents, "odin", "mark", lambda cid, t, *a: self.said.append(t),
            issues=Issues(), log=lambda *a, **k: None, builds=self.builds)
        patcher = mock.patch.object(build, "change_exists", lambda *a, **k: ("", True))
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_build_without_an_issue_opens_one_and_runs_the_chain(self):
        self.try_build("!build ratatoskr x", "odin", "general", "cid", own=True)
        self.assertEqual(self.calls[0][:3], ("create", "ratatoskr", "build: x"))
        argv, kubectl, creds = self.argv[0]
        self.assertTrue(argv[0].endswith("dispatch/chain.sh"))
        self.assertEqual(argv[1:], ["x", "MWest2020/ratatoskr"])
        self.assertEqual((kubectl, creds), ("ssh jumpy kubectl", ""))
        self.assertIn("build started", self.said[-1])

    def test_every_event_lands_on_the_issue(self):
        self.try_build("!build ratatoskr x 12", "odin", "general", "cid", own=True)
        self.tick()
        bodies = [c[3] for c in self.calls if c[0] == "comment" and c[2] == 12]
        self.assertTrue(any("architect: PASS" in b for b in bodies))
        self.assertTrue(any("builder: FAIL" in b for b in bodies))
        self.assertEqual(self.builds.running, [])  # exited, so dropped

    def test_another_agent_cannot_start_one(self):
        self.try_build("!build ratatoskr x", "architect", "general", "cid", own=True)
        self.assertEqual(self.argv, [])
        self.assertIn("only odin or mark", self.said[-1])

    def test_a_refusal_is_said(self):
        self.try_build("!build alma x", "odin", "general", "cid", own=True)
        self.assertEqual(self.argv, [])
        self.assertIn("not on the factory's list", self.said[-1])


if __name__ == "__main__":
    unittest.main()


class Restart(unittest.TestCase):
    """A deploy restarts the listener; a running chain and a waiting PR must
    survive it, and nothing already reported is reported twice."""

    def test_a_restart_picks_up_where_it_left_off(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(t)

            class Alive:
                pid = os.getpid()     # a pid that certainly runs

                def poll(self):
                    return None

            def popen(argv, **kw):
                kw["stdout"].write("=== keten: rol architect ===\nketen: architect -> b1\n")
                return Alive()
            first = build_runner.Builds(c, popen=popen)
            b = first.start("ratatoskr", "x", 7, "general", "cid", "odin")
            seen = []
            first.tick(lambda b, k, r, d: seen.append((k, r)))
            first.merging.append({"repo": "ratatoskr", "pr": 31, "issue": 6, "cid": "c"})
            first.save()
            with open(b["path"], "a") as fh:     # the chain goes on while we restart
                fh.write("=== keten: rol builder ===\nketen: builder -> b2\n")
            second = build_runner.Builds(c, popen=popen)
            second.tick(lambda b, k, r, d: seen.append((k, r)))
            self.assertEqual(seen, [("passed", "architect"), ("passed", "builder")])
            self.assertEqual(len(second.running), 1)
            self.assertEqual(second.merging[0]["pr"], 31)

    def test_a_chain_that_ended_while_we_were_down_is_closed(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(t)
            first = build_runner.Builds(c, popen=lambda argv, **kw: type("P", (), {
                "pid": 2 ** 22 + 12345, "poll": lambda s: None})())
            first.start("ratatoskr", "x", 7, "general", "cid", "odin")
            second = build_runner.Builds(c)
            seen = []
            second.tick(lambda b, k, r, d: seen.append((k, r, d.get("why", ""))))
            self.assertEqual(seen[0][:2], ("failed", "chain"))
            self.assertEqual(second.running, [])
