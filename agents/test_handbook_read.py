# SPDX-License-Identifier: MIT
"""Sessions read handbook main, not a stale copy; a failed refresh is a reason."""
import os
import subprocess
import tempfile
import unittest

import handbook_read


def runner(code=0, stderr=""):
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, code, "", stderr)
    return run, calls


class Refresh(unittest.TestCase):
    def test_creates_then_moves_to_main(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "hb")
            run, calls = runner()
            self.assertEqual(handbook_read.refresh("repo", path, run), "")
            self.assertIn("worktree", calls[1])
            os.makedirs(path)
            run, calls = runner()
            handbook_read.refresh("repo", path, run)
            self.assertEqual(calls[1][-3:], ["-f", "--detach", "origin/main"])

    def test_a_failure_is_a_reason(self):
        run, _ = runner(1, "fatal: unable to access github.com")
        self.assertIn("unable to access", handbook_read.refresh("repo", "/nonexistent", run))
