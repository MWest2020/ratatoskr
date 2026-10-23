# SPDX-License-Identifier: MIT
"""Chat agents read the repos they judge (2026-10-23: the reviewer could not
open wordsworth). Real git against a local origin; no network."""
import os
import subprocess
import tempfile
import unittest

import repo_read

CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, env=CLEAN)


class Sync(unittest.TestCase):
    def test_clone_then_follow_main(self):
        with tempfile.TemporaryDirectory() as t:
            origin = os.path.join(t, "origin", "ww")
            os.makedirs(origin)
            git("init", "-q", "-b", "main", cwd=origin)
            open(os.path.join(origin, "a.md"), "w").write("one\n")
            git("add", ".", cwd=origin)
            git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "1", cwd=origin)

            def run(argv, **kw):          # github URL -> the local origin
                argv = [a.replace("https://github.com/o/ww.git", origin) for a in argv]
                return subprocess.run(argv, env=CLEAN, **kw)
            root = os.path.join(t, "listener")
            self.assertEqual(repo_read.sync(["ww"], "o", root, run, log=lambda *a, **k: None),
                             {"ww": ""})
            open(os.path.join(origin, "a.md"), "w").write("two\n")
            git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "2", cwd=origin)
            repo_read.sync(["ww"], "o", root, run, log=lambda *a, **k: None)
            self.assertEqual(open(os.path.join(root, ".repos", "ww", "a.md")).read(), "two\n")

    def test_a_failure_is_named_not_raised(self):
        def run(argv, **kw):
            return subprocess.CompletedProcess(argv, 128, "", "fatal: repository not found")
        with tempfile.TemporaryDirectory() as t:
            out = repo_read.sync(["x"], "o", t, run, log=lambda *a, **k: None)
        self.assertEqual(out, {"x": "fatal: repository not found"})


class Tick(unittest.TestCase):
    def test_at_most_every_ten_minutes(self):
        calls, clock = [], [0.0]
        tick = repo_read.ticker({"owner": "o", "readable": ["a"]}, "/r", lambda: clock[0],
                                run=lambda argv, **kw: calls.append(argv)
                                or subprocess.CompletedProcess(argv, 0, "", ""))
        tick()
        tick()
        clock[0] = 601
        tick()
        self.assertEqual(len(calls), 2)

    def test_the_clause_names_only_readable_repos(self):
        c = repo_read.clause({"repos": ["zettelkast"], "readable": ["wordsworth"]})
        self.assertIn("`.repos/wordsworth/`", c)
        self.assertNotIn("zettelkast", c)
        self.assertEqual(repo_read.clause({}), "")


if __name__ == "__main__":
    unittest.main()
