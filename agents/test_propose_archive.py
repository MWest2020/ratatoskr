# SPDX-License-Identifier: MIT
"""After a build: the hub is woken for the next step, and a capability the
change created gets a real Purpose so the archive validates (2026-10-24,
convergence fundament). The archive test runs the real openspec CLI."""
import os
import shutil
import subprocess
import tempfile
import unittest

import propose_git
from test_propose import Wiring

CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


class WakeAfterBuild(Wiring):
    def test_a_finished_build_wakes_the_hub_once(self):
        self.done({"repo": "wordsworth", "change": "add-x", "issue": 9, "cid": "cid",
                   "cname": "general"})
        (a, k), = self.turns
        self.assertEqual((a[0], a[8]), ("odin", "build-done"))
        self.assertIn("next step", a[5])
        self.assertTrue(k["followup"])

    def test_proposals_and_archives_wake_nobody_here(self):
        for kind in ("propose", "archive"):
            self.done({"repo": "w", "change": "x", "issue": 1, "cid": "c", "kind": kind})
        self.assertEqual(self.turns, [])


@unittest.skipUnless(shutil.which("openspec"), "openspec CLI not installed")
class FillPurpose(unittest.TestCase):
    def test_a_new_capability_archives_and_validates(self):
        with tempfile.TemporaryDirectory() as wt:
            run = lambda *a: subprocess.run(a, cwd=wt, capture_output=True, text=True, env=CLEAN)  # noqa: E731
            run("openspec", "init", "--tools", "none")
            ch = os.path.join(wt, "openspec", "changes", "add-x")
            os.makedirs(os.path.join(ch, "specs", "newcap"))
            open(os.path.join(ch, "proposal.md"), "w").write(
                "# x\n\n## Why\nThe game needs a ledger. More text.\n\n## What Changes\n- newcap\n")
            open(os.path.join(ch, "tasks.md"), "w").write("# Tasks\n- [x] done\n")
            open(os.path.join(ch, "specs", "newcap", "spec.md"), "w").write(
                "## ADDED Requirements\n\n### Requirement: A ledger\nThe system SHALL keep one.\n\n"
                "#### Scenario: kept\n- **WHEN** asked\n- **THEN** it is kept\n")
            run("openspec", "archive", "add-x", "-y")
            propose_git.fill_purposes(wt, "add-x")
            spec = open(os.path.join(wt, "openspec", "specs", "newcap", "spec.md")).read()
            self.assertIn("Created by the change `add-x`. The game needs a ledger.", spec)
            self.assertNotIn("TBD", spec)
            self.assertEqual(run("openspec", "validate", "--specs", "--strict").returncode, 0)


if __name__ == "__main__":
    unittest.main()
