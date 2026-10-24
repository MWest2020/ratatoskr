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


class ProposeIsNotDeployed(unittest.TestCase):
    def test_a_merged_proposal_wakes_the_hub_and_is_not_deployed(self):
        woke, deployed = [], []

        class Merger:
            def checks(self, *a):
                return "merge", "2 checks passed"

            def merge(self, *a):
                return ""

            def merged_sha(self, *a):
                deployed.append("sha asked")
                return "a" * 40, ""

        class Deployer:
            def recipe(self, repo):
                return {"x": 1}

        class Issues:
            def comment(self, *a):
                return ""
        with tempfile.TemporaryDirectory() as t:
            builds = build_runner.Builds({"owner": "MWest2020", "runs": t}, popen=None)
            builds.merging.append({"repo": "wordsworth", "issue": 9, "cid": "c", "pr": 31,
                                   "next": 0, "kind": "propose"})
            _, tick = build_wiring.setup({"owner": "MWest2020", "runs": t}, {}, "odin", "mark",
                                         lambda *a: True, issues=Issues(), builds=builds,
                                         merger=Merger(), deployer=Deployer(),
                                         after_merge=woke.append, log=lambda *a, **k: None)
            builds.tick = lambda on_event: None
            tick()
        self.assertEqual(len(woke), 1)
        self.assertEqual(deployed, [])
        self.assertEqual(builds.deploying, [])


class CiStopWakesTheHub(unittest.TestCase):
    """2026-10-24: every role passed wordsworth#217, CI failed one test, and
    the listener said "not merged" to nobody who could act."""

    def test_the_hub_gets_the_failing_lines(self):
        woke = []

        class Merger:
            def checks(self, *a):
                return "stop", "failing: Fast test gate (offline)"

            def failure_excerpt(self, *a):
                return "- Fast test gate (offline): FAILED tests/x.py::test_y - AssertionError"

        class Issues:
            def comment(self, *a):
                return ""
        with tempfile.TemporaryDirectory() as t:
            builds = build_runner.Builds({"owner": "MWest2020", "runs": t}, popen=None)
            builds.merging.append({"repo": "wordsworth", "issue": 9, "cid": "c", "pr": 31,
                                   "next": 0, "change": "add-x"})
            _, tick = build_wiring.setup({"owner": "MWest2020", "runs": t}, {}, "odin", "mark",
                                         lambda *a: True, issues=Issues(), builds=builds,
                                         merger=Merger(), after_fail=lambda m, t: woke.append(t),
                                         log=lambda *a, **k: None)
            builds.tick = lambda on_event: None
            tick()
        self.assertEqual(len(woke), 1)
        self.assertIn("FAILED tests/x.py::test_y", woke[0])

    def test_the_excerpt_reads_the_failed_log(self):
        def runner(argv, **kw):
            if argv[:3] == ["gh", "pr", "checks"]:
                out = json.dumps([{"name": "gate", "bucket": "fail",
                                   "link": "https://github.com/o/r/actions/runs/42/job/1"}])
            else:
                out = "gate\tRun tests\t2026-10-24T00:26:42Z \x1b[31mFAILED\x1b[0m tests/a.py::t - boom\n"
            return subprocess.CompletedProcess(argv, 0, out, "")
        self.assertEqual(bm.failure_excerpt("o", "r", 5, runner), "- gate: FAILED tests/a.py::t - boom")
