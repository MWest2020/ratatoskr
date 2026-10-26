# SPDX-License-Identifier: MIT
"""Builds that outlive a restart, and failures that say why (split from
test_build.py for the line limit)."""
import json
import os
import tempfile
import unittest

import build_runner
from test_build import FakeProc, cfg


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


class FailureSaysWhyAndBudget(unittest.TestCase):
    """2026-10-23: wordsworth's builder stopped at the $5 budget after 86 turns;
    the issue said only "FAIL"."""

    def test_the_stop_reason_is_on_the_issue(self):
        with tempfile.TemporaryDirectory() as store:
            json.dump({"verdict": "failed", "subtype": "error_max_budget_usd", "num_turns": 86,
                       "total_cost_usd": 5.0029}, open(os.path.join(store, "run-report.json"), "w"))
            c = build_runner.comment("failed", "builder", {"why": "", "store": store})
        self.assertIn("stopped by `error_max_budget_usd`", c)
        self.assertIn("cost $5.00", c)

    def test_the_budget_reaches_the_chain(self):
        with tempfile.TemporaryDirectory() as t:
            seen = {}

            def popen(argv, **kw):
                seen.update(kw["env"])
                return FakeProc(0)
            build_runner.Builds(cfg(t, max_budget_usd=15), popen=popen).start(
                "ratatoskr", "x", 1, "general", "c", "odin")
        self.assertEqual(seen["HABITAT_MAX_BUDGET_USD"], "15.00")


class ProposeSurvivesRestart(unittest.TestCase):
    def test_a_propose_session_is_adopted_after_a_restart(self):
        with tempfile.TemporaryDirectory() as t:
            first = build_runner.Builds(cfg(t))
            first.proposing.append({"wt": "/wt", "branch": "b", "change": "x", "repo": "ratatoskr",
                                    "issue": 159, "cid": "c", "cname": "general",
                                    "started": 1.0, "pid": os.getpid(), "proc": object()})
            first.save()
            second = build_runner.Builds(cfg(t))
            self.assertEqual(second.proposing[0]["change"], "x")
            self.assertIsNone(second.proposing[0]["proc"].poll())   # still alive: followed


if __name__ == "__main__":
    unittest.main()


class EndedChainLeavesFirst(unittest.TestCase):
    """2026-10-23: a chain killed by a restart woke odin, whose retry was refused
    because the dead chain still counted as running."""

    def test_the_hub_sees_no_running_chain_when_told_it_failed(self):
        import tempfile
        import build_runner
        with tempfile.TemporaryDirectory() as t:
            builds = build_runner.Builds({"runs": t}, popen=None)
            path = f"{t}/r.log"
            open(path, "w").write("{}\n=== keten: rol architect ===\n")

            class Gone:
                def poll(self):
                    return -1
            builds.running.append({"path": path, "proc": Gone(), "seen": 0})
            seen = []
            builds.tick(lambda b, kind, role, d: seen.append((kind, len(builds.running))))
        self.assertIn(("failed", 0), seen)


class Detach(unittest.TestCase):
    def test_wrapped_in_a_scope_when_systemd_is_there(self):
        import detach
        self.assertEqual(detach.argv(["x"], lambda n: "/usr/bin/" + n, {"XDG_RUNTIME_DIR": "/r"})[-1], "x")
        self.assertEqual(detach.argv(["x"], lambda n: "/usr/bin/" + n, {"XDG_RUNTIME_DIR": "/r"})[0],
                         "systemd-run")
        self.assertEqual(detach.argv(["x"], lambda n: None, {}), ["x"])


class FailureSaysWhy(unittest.TestCase):
    def test_a_fail_carries_the_roles_findings_blocking_first(self):
        with tempfile.TemporaryDirectory() as t:
            json.dump({"verdict": "failed", "num_turns": "49", "total_cost_usd": "1.5"},
                      open(os.path.join(t, "run-report.json"), "w"))
            open(os.path.join(t, "run-output-1.md"), "w").write(
                "# x\n\n" + json.dumps({"verdict": "FAIL", "findings": [
                    {"severity": "minor", "location": "t.py:1", "description": "weak test"},
                    {"severity": "blocking", "location": "docs/a.md", "description": "no docs"}]}))
            text = build_runner.comment("failed", "reviewer", {"store": t, "why": "(exit 1)"})
        self.assertIn("cost $1.50", text)
        self.assertLess(text.index("[blocking] docs/a.md: no docs"), text.index("[minor]"))

    def test_no_output_no_findings(self):
        self.assertEqual(build_runner.findings("/nonexistent"), [])


class DetachReachesTheBus(unittest.TestCase):
    """2026-10-24: a propose session's trimmed env had no XDG_RUNTIME_DIR, so
    systemd-run could not reach the bus and the session never ran."""

    def test_the_child_env_carries_the_bus(self):
        import detach
        e = detach.env({"PATH": "/bin"}, {"XDG_RUNTIME_DIR": "/run/user/1", "SECRET": "x"})
        self.assertEqual(e, {"PATH": "/bin", "XDG_RUNTIME_DIR": "/run/user/1"})

    def test_wrapping_is_decided_on_the_childs_env(self):
        import detach
        self.assertEqual(detach.argv(["x"], lambda n: "/bin/" + n, env={"PATH": "/bin"}), ["x"])


class VerdictAnywhere(unittest.TestCase):
    def test_a_verdict_key_after_the_summary_is_found(self):
        with tempfile.TemporaryDirectory() as t:
            open(os.path.join(t, "run-output-1.md"), "w").write("# r\n\n" + json.dumps(
                {"summary": "x", "verdict": "FAIL",
                 "findings": [{"severity": "blocking", "location": "a", "description": "b"}]}))
            self.assertEqual(build_runner.findings(t), ["- [blocking] a: b"])


class HandbookRefReachesHabitat(unittest.TestCase):
    """2026-10-26: the roles come from the handbook at a pinned commit."""
    CFG = {"worker_image": "w:1", "kubectl": "k", "logdir": "/l"}

    def test_the_pin_is_passed_when_set(self):
        e = build_runner.child_env({**self.CFG, "handbook_ref": "3e0d0a1"}, "x", {})
        self.assertEqual(e["HABITAT_HANDBOOK_REF"], "3e0d0a1")

    def test_no_pin_no_variable(self):
        self.assertNotIn("HABITAT_HANDBOOK_REF", build_runner.child_env(self.CFG, "x", {}))
