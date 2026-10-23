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


if __name__ == "__main__":
    unittest.main()
