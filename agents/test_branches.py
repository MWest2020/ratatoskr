# SPDX-License-Identifier: MIT
"""A finished chain takes its branches with it, and the factory proposes a
change once (Mark, 2026-10-24: "too many branches", "proposals on the same
topic ... kinda bad"). Offline; gh is faked."""
import subprocess
import unittest

import branches
from test_propose import Builds, Proc, Wiring

RUN = ["=== keten: rol architect ===", "[dispatch] branch=habitat/architect/x-1",
       "=== keten: rol builder ===", "[dispatch] branch=habitat/builder/x-2",
       "[dispatch] branch=habitat/builder/x-2", "=== keten: rol reviewer ===",
       "[dispatch] branch=habitat/reviewer/x-3"]


class Branches(unittest.TestCase):
    def runner(self):
        calls = []

        def run(argv, **kw):
            calls.append(argv[-1].rsplit("/heads/", 1)[-1])
            return subprocess.CompletedProcess(argv, 0, "", "")
        return run, calls

    def test_a_passed_chain_keeps_only_the_builder_branch(self):
        run, calls = self.runner()
        branches.delete("o", "r", branches.of_chain(RUN), keep=("habitat/builder/x-2",), runner=run)
        self.assertEqual(calls, ["habitat/architect/x-1", "habitat/reviewer/x-3"])

    def test_main_and_foreign_branches_are_never_deleted(self):
        run, calls = self.runner()
        branches.delete("o", "r", ["main", "feature/mine", "habitat/builder/y"], runner=run)
        self.assertEqual(calls, ["habitat/builder/y"])


class OneProposalPerChange(Wiring):
    def test_a_change_in_flight_is_not_proposed_twice(self):
        self.try_p("!propose wordsworth add-x Do x.", "odin", "general", "cid", [], "mark")
        self.try_p("!propose wordsworth add-x Do x again.", "odin", "general", "cid", [], "mark")
        self.assertEqual(len(self.started), 1)
        self.assertIn("already being written", self.said[-1])

    def test_a_change_waiting_for_ci_is_not_proposed_twice(self):
        self.builds.merging.append({"repo": "wordsworth", "change": "add-x", "kind": "propose", "pr": 31})
        self.try_p("!propose wordsworth add-x Do x.", "odin", "general", "cid", [], "mark")
        self.assertEqual(self.started, [])
        self.assertIn("already proposed in PR #31", self.said[-1])


if __name__ == "__main__":
    unittest.main()
