# SPDX-License-Identifier: MIT
"""`chain_wiring`: reading proposals, deciding "merged", and the outcomes of
`chain(m)` — one test per outcome, each asserting whether `try_build` was
called (AGENTS.md: a seam needs a test that pins the title the build-merge
road writes against the one this module searches for)."""
import json
import subprocess
import unittest

import build_merge
import chain_wiring

OWNER, REPO = "MWest2020", "wordsworth"


def gh(code=0, out="", err=""):
    return lambda argv, **kw: subprocess.CompletedProcess(argv, code, out, err)


class ReadProposal(unittest.TestCase):
    def test_the_raw_header_is_in_the_call(self):
        seen = []

        def runner(argv, **kw):
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, "## Next\n`b`\n", "")
        text, err = chain_wiring.read_proposal(OWNER, REPO, "a", runner)
        self.assertEqual(err, "")
        self.assertIn("Accept: application/vnd.github.raw+json", seen[0])

    def test_a_gh_error_is_a_failed_read(self):
        text, err = chain_wiring.read_proposal(OWNER, REPO, "a", gh(1, "", "not found"))
        self.assertEqual(text, "")
        self.assertIn("not found", err)

    def test_a_json_body_is_a_failed_read(self):
        text, err = chain_wiring.read_proposal(OWNER, REPO, "a",
                                               gh(0, '{"message": "Not Found"}'))
        self.assertEqual(text, "")
        self.assertNotEqual(err, "")


class Merged(unittest.TestCase):
    def test_the_just_merged_change_counts(self):
        self.assertTrue(chain_wiring.merged(OWNER, REPO, "a", "a", gh(1)))

    def test_a_merged_build_pr_of_the_parent_counts(self):
        out = json.dumps([{"title": "build: a"}])
        self.assertTrue(chain_wiring.merged(OWNER, REPO, "a", "x", gh(0, out)))

    def test_a_near_miss_title_does_not_count(self):
        out = json.dumps([{"title": "build: a-extra"}])
        self.assertFalse(chain_wiring.merged(OWNER, REPO, "a", "x", gh(0, out)))

    def test_no_merged_pr_does_not_count(self):
        self.assertFalse(chain_wiring.merged(OWNER, REPO, "a", "x", gh(0, "[]")))

    def test_the_title_build_merge_writes_is_what_this_searches_for(self):
        pr, err = build_merge.open_pr(OWNER, REPO, "habitat/builder/a-1", "a", 9, [],
                                      runner=gh(0, "https://github.com/x/y/pull/31\n"))
        self.assertEqual(err, "")
        out = json.dumps([{"title": "build: a"}])
        self.assertTrue(chain_wiring.merged(OWNER, REPO, "a", "x", gh(0, out)))


class Chain(unittest.TestCase):
    def setUp(self):
        self.said, self.logged, self.requested = [], [], []
        self.proposals = {}
        self.archive = []
        self.merged_titles = []

    def runner(self, argv, **kw):
        joined = " ".join(argv)
        if "proposal.md" in joined:
            change = next(a for a in argv if a.startswith("repos/")).split("/")[6]
            text = self.proposals.get(change)
            if text is None:
                return subprocess.CompletedProcess(argv, 1, "", "not found")
            return subprocess.CompletedProcess(argv, 0, text, "")
        if "contents/openspec/changes/archive" in joined:
            out = "\n".join(f"2026-11-05-{c}" for c in self.archive)
            return subprocess.CompletedProcess(argv, 0, out, "")
        if argv[:2] == ["gh", "pr"] and "list" in argv:
            out = json.dumps([{"title": t} for t in self.merged_titles])
            return subprocess.CompletedProcess(argv, 0, out, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def chain(self):
        return chain_wiring.setup(
            {"owner": OWNER}, "odin", lambda cid, t: self.said.append((cid, t)),
            lambda *a, **k: self.requested.append((a, k)), runner=self.runner,
            log=lambda *a, **k: self.logged.append(a[0]))

    def test_a_failed_read_is_not_a_missing_next_step(self):
        self.chain()({"repo": REPO, "change": "a", "cid": "c"})
        self.assertEqual(self.requested, [])
        self.assertIn("could not read", self.said[0][1])

    def test_no_next_step_named(self):
        self.proposals["a"] = "## Why\nx\n"
        self.chain()({"repo": REPO, "change": "a", "cid": "c"})
        self.assertEqual(self.requested, [])
        self.assertIn("names no next step", self.said[0][1])

    def test_a_malformed_next_section(self):
        self.proposals["a"] = "## Next\nSomeone decides.\n"
        self.chain()({"repo": REPO, "change": "a", "cid": "c"})
        self.assertEqual(self.requested, [])
        self.assertIn("names no change", self.said[0][1])

    def test_the_next_step_already_archived_is_a_loop_guard(self):
        self.proposals["a"] = "## Next\n`b`\n"
        self.archive = ["b"]
        self.chain()({"repo": REPO, "change": "a", "cid": "c"})
        self.assertEqual(self.requested, [])
        self.assertIn("already archived", self.said[0][1])

    def test_a_parent_not_merged_is_named(self):
        self.proposals["a"] = "## Next\n`b`\n"
        self.proposals["b"] = "## Depends on\n`c`\n"
        self.chain()({"repo": REPO, "change": "a", "cid": "c"})
        self.assertEqual(self.requested, [])
        self.assertIn("`c`", self.said[0][1])

    def test_a_deploy_precondition_waits_for_a_person(self):
        self.proposals["a"] = "## Next\n`b`\n"
        self.proposals["b"] = "## Deploy precondition\nRestore a backup first.\n"
        self.chain()({"repo": REPO, "change": "a", "cid": "c"})
        self.assertEqual(self.requested, [])
        self.assertIn("a person starts it", self.said[0][1])

    def test_requested_when_every_gate_is_open(self):
        self.proposals["a"] = "## Next\n`b`\n"
        self.proposals["b"] = "## Depends on\n`a`\n"
        self.chain()({"repo": REPO, "change": "a", "cid": "c", "cname": "general"})
        self.assertEqual(len(self.requested), 1)
        args, kw = self.requested[0]
        self.assertEqual(args[0], f"!build {REPO} b")
        self.assertEqual((args[1], args[2], args[3]), ("odin", "general", "c"))
        self.assertTrue(kw["own"])

    def test_an_entry_with_no_cid_logs_instead_of_saying(self):
        self.chain()({"repo": REPO, "change": "a"})
        self.assertEqual(self.said, [])
        self.assertTrue(self.logged)


if __name__ == "__main__":
    unittest.main()
