# SPDX-License-Identifier: MIT
"""The propose road: a decided change is written by a fenced session and checked
by the listener (2026-10-23: the decision for ingest-records-source had nobody
to write it). `check` runs against a real git worktree; the model, gh and
openspec are faked."""
import os
import subprocess
import tempfile
import unittest

import propose
import propose_wiring

CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, env=CLEAN)


class Check(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.wt = self.t.name
        git("init", "-q", "-b", "main", cwd=self.wt)
        open(os.path.join(self.wt, "README.md"), "w").write("x\n")
        git("add", ".", cwd=self.wt)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed", cwd=self.wt)
        self.job = {"wt": self.wt, "change": "add-x"}

    def tearDown(self):
        self.t.cleanup()

    def run_(self, validate_code=0):
        def run(argv, **kw):
            if argv[0] == "openspec":
                return subprocess.CompletedProcess(argv, validate_code, "ok", "bad delta")
            return subprocess.run(argv, env=CLEAN, **kw)
        return run

    def write(self, rel):
        p = os.path.join(self.wt, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write("text\n")

    def test_a_valid_change_passes(self):
        self.write("openspec/changes/add-x/proposal.md")
        self.assertEqual(propose.check(self.job, self.run_()), "")

    def test_nothing_written_is_said(self):
        self.assertEqual(propose.check(self.job, self.run_()), "the session wrote nothing")

    def test_a_file_outside_the_change_is_refused(self):
        self.write("openspec/changes/add-x/proposal.md")
        self.write("src/evil.py")
        self.assertIn("files outside openspec/changes/add-x/", propose.check(self.job, self.run_()))

    def test_a_failing_git_status_is_an_error_not_nothing(self):
        def run(argv, **kw):
            return subprocess.CompletedProcess(argv, 128, "", "fatal: must be run in a work tree")
        self.assertIn("git status failed", propose.check(self.job, run))

    def test_validation_is_read_from_the_exit_code(self):
        self.write("openspec/changes/add-x/proposal.md")
        self.assertIn("openspec validate failed", propose.check(self.job, self.run_(1)))


class Fence(unittest.TestCase):
    def test_tools_are_fenced_to_the_change(self):
        t = propose.tools("add-x")
        self.assertIn("Write(./openspec/changes/add-x/**)", t)
        self.assertIn("Bash(openspec validate add-x --strict)", t)
        self.assertNotIn("Write", t)
        self.assertNotIn("Bash", t)

    def test_first_line_only(self):
        self.assertEqual(propose.read_marker("!propose wordsworth add-x Do x.\nok"),
                         ("wordsworth", "add-x", "Do x."))
        self.assertIsNone(propose.read_marker("quote:\n!propose wordsworth add-x Do x."))


class Proc:
    def __init__(self, code):
        self.code = code

    def poll(self):
        return self.code


class Builds:
    def __init__(self):
        self.merging = []
        self.proposing = []

    def save(self):
        pass


class Wiring(unittest.TestCase):
    def setUp(self):
        self.said, self.turns, self.started = [], [], []
        self.builds = Builds()

        class Issues:
            def create(s, repo, title, body, labels):
                return 9, "u", ""

            def comment(s, *a):
                return ""

        def start(clone, change, summary, msgs, pub2name, requester):
            self.started.append((clone, change))
            return {"wt": "/wt", "branch": "b", "change": change, "proc": Proc(0),
                    "summary": summary}, ""
        cfg = {"owner": "MWest2020", "repos": ["wordsworth"]}
        self.try_p, self.tick, self.after, self.fail, self.done = propose_wiring.setup(
            cfg, {"odin": {"nsec": "n", "npub": "p"}}, "odin",
            lambda cid, t, *a: self.said.append(t), {}, self.builds,
            lambda cid: [{"content": "decided"}], lambda *a, **k: self.turns.append((a, k)),
            issues=Issues(), log=lambda *a, **k: None, start=start,
            check=lambda j: "", publish=lambda j, repo, owner: (31, ""),
            archive=lambda clone, repo, owner, change: (44, ""))

    def test_from_marker_to_a_merge_queued_without_deploy(self):
        self.try_p("!propose wordsworth add-x Do x.", "odin", "general", "cid", [], "mark")
        self.assertTrue(self.started[0][0].endswith("/wordsworth"))
        self.tick()
        m = self.builds.merging[0]
        self.assertEqual((m["pr"], m["kind"], m["change"], m["cname"]), (31, "propose", "add-x", "general"))
        self.assertIn("proposed in PR #31", self.said[-1])

    def test_only_the_hub_and_only_listed_repos(self):
        self.try_p("!propose wordsworth add-x Do x.", "architect", "general", "cid", [], "mark")
        self.try_p("!propose alma add-x Do x.", "odin", "general", "cid", [], "mark")
        self.assertEqual(self.started, [])
        self.assertIn("not on the factory's list", self.said[-1])

    def test_a_merged_proposal_wakes_the_hub_to_build(self):
        self.after({"kind": "propose", "repo": "wordsworth", "change": "add-x", "issue": 9,
                    "pr": 31, "cid": "cid", "cname": "general"})
        a, k = self.turns[0]
        self.assertEqual(a[0], "odin")
        self.assertIn("!build wordsworth add-x 9", a[5])
        self.assertTrue(k["followup"])
        self.after({"kind": None, "repo": "x"})              # a build's merge wakes nobody
        self.assertEqual(len(self.turns), 1)


if __name__ == "__main__":
    unittest.main()


class FailureWakesTheHub(Wiring):
    def test_a_failed_build_wakes_the_hub_to_decide(self):
        self.fail({"repo": "wordsworth", "change": "x", "issue": 9, "cid": "cid",
                   "cname": "general"}, "**builder: FAIL** (stopped by `error_max_budget_usd`)")
        a, k = self.turns[0]
        self.assertEqual((a[0], a[8]), ("odin", "build-failed"))
        self.assertIn("error_max_budget_usd", a[5])
        self.assertTrue(k["followup"])



class ArchiveAfterDone(Wiring):
    def test_a_done_change_is_archived_by_pr(self):
        self.done({"repo": "wordsworth", "change": "add-x", "issue": 9, "cid": "cid"})
        m = self.builds.merging[-1]
        self.assertEqual((m["pr"], m["kind"], m["change"]), (44, "archive", "add-x"))
        self.assertIn("archiving `add-x` in PR #44", self.said[-1])

    def test_proposals_and_archives_are_not_archived_again(self):
        for kind in ("propose", "archive"):
            self.done({"repo": "wordsworth", "change": "add-x", "issue": 9, "cid": "c",
                       "kind": kind})
        self.assertEqual(self.builds.merging, [])


class LongSummary(unittest.TestCase):
    """2026-10-24: odin's summaries ran to ~400 characters and were dropped."""
    LONG = "!propose wordsworth pilot-ingest-manifest " + "Extend the ingest. " * 20

    def test_a_long_summary_is_read(self):
        self.assertEqual(propose.read_marker(self.LONG)[1], "pilot-ingest-manifest")

    def test_a_line_that_does_not_parse_is_said(self):
        self.assertIn("not understood", propose.unread("!propose wordsworth X Bad id."))
        self.assertEqual(propose.unread(self.LONG), "")
        self.assertEqual(propose.unread("no marker"), "")
