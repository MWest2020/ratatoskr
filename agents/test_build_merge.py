# SPDX-License-Identifier: MIT
"""Phase 2: after the chain, a PR; after CI, a merge. Only a branch every check
passed is merged, and nothing verified means nothing merged. Offline."""
import json
import subprocess
import tempfile
import unittest

import build_merge as bm
import build_runner
import build_wiring


def gh(rows=None, code=0, stderr="", stdout=None):
    calls = []

    def runner(argv, **kw):
        calls.append((argv, kw.get("input")))
        out = stdout if stdout is not None else json.dumps(rows or [])
        return subprocess.CompletedProcess(argv, code, out, stderr)
    return runner, calls


class Checks(unittest.TestCase):
    def verdict(self, rows, **kw):
        return bm.checks("MWest2020", "ratatoskr", 5, gh(rows, **kw)[0])[0]

    def test_all_passed_is_a_merge(self):
        self.assertEqual(self.verdict([{"name": "verify", "bucket": "pass"},
                                       {"name": "lint", "bucket": "skipping"}]), "merge")

    def test_pending_waits(self):
        self.assertEqual(self.verdict([{"name": "verify", "bucket": "pending"}], code=8), "wait")

    def test_a_failure_stops_and_names_it(self):
        v, why = bm.checks("MWest2020", "ratatoskr", 5, gh([{"name": "verify", "bucket": "fail"},
                                                            {"name": "x", "bucket": "pass"}])[0])
        self.assertEqual((v, why), ("stop", "failing: verify"))

    def test_nothing_verified_is_no_merge(self):
        self.assertEqual(self.verdict([]), "wait")
        self.assertEqual(self.verdict([{"name": "a", "bucket": "skipping"}]), "wait")
        self.assertEqual(self.verdict(None, code=1, stderr="no checks reported on the 'x' branch"),
                         "wait")

    def test_an_unreadable_answer_stops(self):
        self.assertEqual(self.verdict(None, code=1, stderr="HTTP 401"), "stop")


class OpenPr(unittest.TestCase):
    def test_the_pr_closes_the_issue_and_the_body_goes_on_stdin(self):
        runner, calls = gh(stdout="https://github.com/MWest2020/ratatoskr/pull/31\n")
        n, err = bm.open_pr("MWest2020", "ratatoskr", "habitat/builder/x-1", "x", 157,
                            ["architect: PASS"], runner)
        self.assertEqual((n, err), (31, ""))
        argv, body = calls[0]
        self.assertIn("--head=habitat/builder/x-1", argv)
        self.assertIn("Closes #157", body)
        self.assertNotIn("Closes #157", " ".join(argv))


class Flow(unittest.TestCase):
    def test_chain_done_to_merged(self):
        said, comments, merged = [], [], []
        clock = [1000.0]

        class Merger:
            def open_pr(self, owner, repo, branch, change, issue, verdicts):
                return 31, ""

            def checks(self, owner, repo, pr):
                return ("wait", "pending") if clock[0] < 1100 else ("merge", "3 checks passed")

            def merge(self, owner, repo, pr):
                merged.append(pr)
                return ""

        class Issues:
            def comment(self, repo, n, body):
                comments.append(body)
                return ""

        with tempfile.TemporaryDirectory() as t:
            cfg = {"owner": "MWest2020", "runs": t}
            builds = build_runner.Builds(cfg, popen=None)
            _, tick = build_wiring.setup(cfg, {"odin": {"nsec": "n", "npub": "p"}}, "odin",
                                         "mark", lambda cid, text, *a: said.append(text),
                                         issues=Issues(), log=lambda *a, **k: None,
                                         builds=builds, merger=Merger(), now=lambda: clock[0])
            b = {"repo": "ratatoskr", "change": "x", "issue": 157, "cid": "c"}
            builds.tick = lambda on_event: [on_event(b, "done", "chain",
                                                     {"branch": "habitat/builder/x-1"})]
            tick()                       # chain done -> PR opened, checks pending
            builds.tick = lambda on_event: None
            self.assertEqual(merged, [])
            clock[0] = 1200.0
            tick()                       # checks passed -> merged
        self.assertEqual(merged, [31])
        self.assertTrue(any("PR #31 opened" in c for c in comments))
        self.assertTrue(any("Merged PR #31" in c for c in comments))
        self.assertTrue(said[-1].startswith("✅ merged PR #31"))


if __name__ == "__main__":
    unittest.main()
