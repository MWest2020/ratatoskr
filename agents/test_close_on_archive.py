# SPDX-License-Identifier: MIT
"""A fake main (the `gh` runner replaced) for close_on_archive.tick_repo and
close_on_archive.ticker. The fake plays both sides a real listener depends on:
the listing of open build:/propose: issues, the listing of openspec/changes
and its archive, and the closing side (an Issues double), so a change in the
contract on either side fails this test (AGENTS.md: a seam needs a test that
calls both sides)."""
import json
import unittest

import close_on_archive

OWNER = "MWest2020"


class FakeMain:
    def __init__(self):
        self.open_issues = {}   # repo -> [(number, title)]
        self.changes = {}       # repo -> [change id still on main]
        self.archive = {}       # repo -> [dated archive dir name]
        self.fail = {}          # repo -> "issues" | "changes" | "archive"
        self.calls = []

    def _repo(self, argv):
        for a in argv:
            if a.startswith("--repo="):
                return a.split("/", 1)[1]
            if a.startswith("repos/"):
                return a.split("/")[2]
        return ""

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        repo = self._repo(argv)
        joined = " ".join(argv)

        class R:
            pass
        r = R()
        r.returncode, r.stderr, r.stdout = 0, "", ""
        if "issue" in argv and "list" in argv:
            kind = "issues"
            rows = [{"number": n, "title": t} for n, t in self.open_issues.get(repo, [])]
            out = json.dumps(rows)
        elif "contents/openspec/changes/archive" in joined:
            kind = "archive"
            out = "\n".join(self.archive.get(repo, []))
        else:
            kind = "changes"
            out = "\n".join(self.changes.get(repo, []))
        if self.fail.get(repo) == kind:
            r.returncode, r.stderr = 1, "rate limited"
        else:
            r.stdout = out
        return r


class FakeIssues:
    def __init__(self, fail_numbers=()):
        self.closed = []
        self.fail_numbers = set(fail_numbers)

    def close(self, repo, number, body):
        if number in self.fail_numbers:
            return "gh refused"
        self.closed.append((repo, number, body))
        return ""

    def open_titled(self, repo, title):
        return []


class TickRepo(unittest.TestCase):
    def setUp(self):
        self.main = FakeMain()
        self.issues = FakeIssues()
        self.log = []

    def tick(self, repo="r"):
        close_on_archive.tick_repo(OWNER, repo, issues=self.issues, runner=self.main,
                                   log=lambda *a, **k: self.log.append(a[0]))

    def test_archive_closes_build_and_propose_with_the_archive_path(self):
        self.main.open_issues["r"] = [(5, "build: add-x"), (6, "propose: add-x")]
        self.main.changes["r"] = ["other-change"]
        self.main.archive["r"] = ["2026-10-24-add-x"]
        self.tick()
        self.assertEqual({n for _, n, _ in self.issues.closed}, {5, 6})
        self.assertTrue(all("openspec/changes/archive/2026-10-24-add-x" in b
                            for _, _, b in self.issues.closed))

    def test_removal_without_archive_stays_open_and_is_logged(self):
        self.main.open_issues["r"] = [(5, "build: add-x")]
        self.main.changes["r"] = []
        self.main.archive["r"] = []
        self.tick()
        self.assertEqual(self.issues.closed, [])
        self.assertTrue(any("add-x" in line for line in self.log))

    def test_a_change_still_on_main_is_untouched(self):
        self.main.open_issues["r"] = [(5, "build: add-x")]
        self.main.changes["r"] = ["add-x"]
        self.main.archive["r"] = []
        self.tick()
        self.assertEqual(self.issues.closed, [])
        self.assertEqual(self.log, [])

    def test_a_gh_failure_skips_the_tick_for_that_repository(self):
        self.main.open_issues["r"] = [(5, "build: add-x")]
        self.main.fail["r"] = "changes"
        self.tick()
        self.assertEqual(self.issues.closed, [])
        self.assertTrue(any("r" in line for line in self.log))

    def test_a_failing_close_is_logged_and_the_other_issue_still_closes(self):
        self.main.open_issues["r"] = [(5, "build: add-x"), (6, "propose: add-x")]
        self.main.changes["r"] = []
        self.main.archive["r"] = ["2026-10-24-add-x"]
        self.issues.fail_numbers = {5}
        self.tick()
        self.assertEqual([n for _, n, _ in self.issues.closed], [6])
        self.assertTrue(any("5" in line for line in self.log))

    def test_only_repos_with_an_open_issue_are_polled(self):
        self.main.open_issues["r"] = [(5, "build: add-x"), (6, "propose: add-x")]
        self.main.changes["r"] = []
        self.main.archive["r"] = ["2026-10-24-add-x"]
        self.tick()
        # one issue-list call, then at most one pair of listing calls — not one per issue
        self.assertEqual(len(self.main.calls), 3)

    def test_no_open_issue_polls_nothing_else(self):
        self.tick()
        self.assertEqual(len(self.main.calls), 1)
        self.assertEqual(self.issues.closed, [])


class Restart(unittest.TestCase):
    def test_empty_state_closes_then_a_second_tick_is_quiet(self):
        main, issues = FakeMain(), FakeIssues()
        main.open_issues["r"] = [(5, "build: add-x")]
        main.changes["r"] = []
        main.archive["r"] = ["2026-10-24-add-x"]
        clock = [0.0]
        tick = close_on_archive.ticker(OWNER, ["r"], issues=issues, runner=main,
                                       now=lambda: clock[0], log=lambda *a, **k: None)
        tick()
        self.assertEqual([n for _, n, _ in issues.closed], [5])
        main.open_issues["r"] = []   # now closed: gh issue list no longer returns it
        clock[0] += close_on_archive.TICK_S
        tick()
        self.assertEqual(len(issues.closed), 1)


if __name__ == "__main__":
    unittest.main()
