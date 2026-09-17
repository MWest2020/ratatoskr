# SPDX-License-Identifier: MIT
"""Tests for the work overview. Only the PURE side: column choice, age and
staleness. Those decide what the board says, and you want to test them without
GitHub and without a clock.

Run with: cd jobs && python3 -m unittest test_board
"""
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board  # noqa: E402
import board_model  # noqa: E402
import board_github  # noqa: E402
import board_sources  # noqa: E402

COLUMNS = [{"key": "proposal", "title": "voorstel", "stale_days": 14},
           {"key": "building", "title": "bouwen", "stale_days": 3},
           {"key": "review", "title": "review", "stale_days": 2},
           {"key": "merged", "title": "gemerged", "stale_days": 0}]


class OpenspecCards(unittest.TestCase):
    def test_archive_is_skipped(self):
        d = tempfile.mkdtemp()
        live = os.path.join(d, "home", "agent", "repo", "openspec", "changes", "nieuw")
        dead = os.path.join(d, "home", "agent", "repo", "openspec", "changes", "archive", "oud")
        for p in (live, dead):
            os.makedirs(p)
            open(os.path.join(p, "proposal.md"), "w").write("x")
        got = board_sources.openspec_cards(os.path.join(d, "home/agent/*/openspec/changes/*/proposal.md"),
                                   time.time())
        self.assertEqual([c["title"] for c in got], ["nieuw"])

    def test_a_worktree_is_not_a_second_repo(self):
        """Sessions work in their own worktree of the same repo. Counting those
        made one change appear three times, and kept it on the board after it
        was archived on main — the worktree still holds the old branch."""
        d = tempfile.mkdtemp()
        for naam, git in [("repo", "dir"), ("repo-worktree", "file")]:
            change = os.path.join(d, "home", "agent", naam, "openspec", "changes", "iets")
            os.makedirs(change)
            open(os.path.join(change, "proposal.md"), "w").write("x")
            g = os.path.join(d, "home", "agent", naam, ".git")
            os.makedirs(g) if git == "dir" else open(g, "w").write("gitdir: /elders\n")
        got = board_sources.openspec_cards(os.path.join(d, "home/agent/*/openspec/changes/*/proposal.md"),
                                   time.time())
        self.assertEqual([c["repo"] for c in got], ["repo"])

    def test_a_directory_without_git_still_counts(self):
        """The test is 'is this a worktree', not 'is this a clone'. A checkout
        without a .git at all (a tarball, a copy) is not a reason to hide work."""
        d = tempfile.mkdtemp()
        change = os.path.join(d, "home", "agent", "repo", "openspec", "changes", "iets")
        os.makedirs(change)
        open(os.path.join(change, "proposal.md"), "w").write("x")
        got = board_sources.openspec_cards(os.path.join(d, "home/agent/*/openspec/changes/*/proposal.md"),
                                   time.time())
        self.assertEqual(len(got), 1)

class Links(unittest.TestCase):
    """A card without a link is a dead end; a card to a 404 is worse. That is why
    the URL comes from the clone's remote, not from the directory name."""

    def test_openspec_card_links_to_the_change(self):
        d = tempfile.mkdtemp()
        clone = os.path.join(d, "home", "agent", "repo")
        change = os.path.join(clone, "openspec", "changes", "iets")
        os.makedirs(change)
        open(os.path.join(change, "proposal.md"), "w").write("x")
        board_sources.repo_url = lambda c: "https://github.com/MWest2020/repo"
        got = board_sources.openspec_cards(os.path.join(d, "home/agent/*/openspec/changes/*/proposal.md"),
                                   time.time())
        self.assertEqual(got[0]["url"],
                         "https://github.com/MWest2020/repo/tree/main/openspec/changes/iets")

    def test_no_remote_means_no_url_not_a_guess(self):
        d = tempfile.mkdtemp()
        change = os.path.join(d, "home", "agent", "repo", "openspec", "changes", "iets")
        os.makedirs(change)
        open(os.path.join(change, "proposal.md"), "w").write("x")
        board_sources.repo_url = lambda c: ""
        got = board_sources.openspec_cards(os.path.join(d, "home/agent/*/openspec/changes/*/proposal.md"),
                                   time.time())
        self.assertEqual(got[0]["url"], "")

    def test_session_card_carries_its_channel(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "zettelkast-mark-1.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"type": "boomhuis_session", "channel": "general",
                                "requester": "mark"}) + "\n")
        got = board_sources.session_cards(d, time.time())
        self.assertEqual(got[0]["channel"], "general")
        self.assertEqual(got[0]["who"], "mark")



ROW_MERGED = {"repository": {"name": "repo"}, "number": 125, "title": "iets",
              "updatedAt": "2026-09-13T16:00:05Z", "url": "", "isDraft": False,
              "author": {"login": "a"}, "merged": True}


class Snapshot(unittest.TestCase):
    """De PR-kant. De issue-bron heeft een eigen cache in dezelfde tempmap, zodat
    geen enkele test het gedeelde /tmp-pad raakt of de andere beinvloedt."""

    def setUp(self):
        # Elke test hier gaat over PR's; de issue-bron doet hier niet mee en
        # moet dus ook geen kaarten of fouten bijdragen.
        self._echt = board_github.issue_rows
        board_github.issue_rows = lambda owner: []

    def tearDown(self):
        board_github.issue_rows = self._echt

    def cfg(self, cache, seconds):
        return {"columns": COLUMNS,
                "sources": {"openspec_glob": "/bestaat/niet/*", "github_owner": "x",
                            "session_runs": "/bestaat/niet", "merged_days": 3,
                            "pr_cache": cache, "pr_cache_seconds": seconds,
                            "issue_cache": cache + ".issues"}}

    def test_failing_source_becomes_an_error_not_silence(self):
        """Silently showing nothing is indistinguishable from 'nothing to do'."""
        empty = os.path.join(tempfile.mkdtemp(), "geen-cache.json")
        cfg = {"columns": COLUMNS,
               "sources": {"openspec_glob": "/bestaat/niet/*", "github_owner": "x",
                           "session_runs": "/bestaat/niet", "merged_days": 3,
                           "pr_cache": empty, "pr_cache_seconds": 600,
                           "issue_cache": empty + ".issues"}}
        board_github.gh_json = lambda args: (_ for _ in ()).throw(RuntimeError("gh weg"))
        snap = board.build(cfg, now=1000.0)
        self.assertTrue(snap["errors"])
        self.assertIn("gh weg", snap["errors"][0])
        self.assertEqual(snap["cards"], [])

    def test_a_stale_merged_cache_is_used_but_announced(self):
        """Een oude cache is beter dan een leeg bord — zolang het bord zegt dat
        hij oud is. Stilletjes oude PR's tonen is de valse groenmelding in
        vermomming."""
        cache = os.path.join(tempfile.mkdtemp(), "prs.json")
        with open(cache, "w") as f:
            json.dump({"at": 0, "rows": [ROW_MERGED]}, f)
        cfg = self.cfg(cache, 1)
        board_github.gh_json = lambda args: (_ for _ in ()).throw(RuntimeError("gh weg"))
        snap = board.build(cfg, now=1000.0)
        self.assertEqual(len(snap["cards"]), 1)
        self.assertTrue(any("not refreshed" in e for e in snap["errors"]), snap["errors"])

    def test_a_fresh_cache_skips_the_merged_query_but_not_the_open_one(self):
        """Het cachen bestaat om het bord elke twee minuten te kunnen draaien.
        Maar de OPEN kant hoort daar niet bij: dat is de kolom waar iemand iets
        mee moet, en die mag niet tien minuten achterlopen."""
        cache = os.path.join(tempfile.mkdtemp(), "prs.json")
        with open(cache, "w") as f:
            json.dump({"at": 999.0, "rows": []}, f)
        gevraagd = []

        def gh(args):
            gevraagd.append(" ".join(args))
            if "--state=open" in args:
                return []
            raise AssertionError("de gemergede kant had uit de cache moeten komen")

        board_github.gh_json = gh
        snap = board.build(self.cfg(cache, 600), now=1000.0)
        self.assertEqual(snap["errors"], [])
        self.assertEqual(len(gevraagd), 1, gevraagd)
        self.assertIn("--state=open", gevraagd[0])

    def test_a_just_merged_pr_does_not_linger_in_review(self):
        """De regressie die dit veroorzaakte, 2026-09-13: #125 stond acht
        minuten na zijn merge nog in review, omdat de open kant uit dezelfde
        cache kwam als de gemergede kant. Een kaart in 'review' die om niets
        vraagt, leert je de kolom te negeren."""
        cache = os.path.join(tempfile.mkdtemp(), "prs.json")
        # De cache is VERS en bevat de PR nog als open — precies de situatie.
        with open(cache, "w") as f:
            json.dump({"at": 999.0, "rows": [ROW_MERGED]}, f)
        board_github.gh_json = lambda args: [] if "--state=open" in args else []
        snap = board.build(self.cfg(cache, 600), now=1000.0)
        kolommen = [c["column"] for c in snap["cards"]]
        self.assertNotIn("review", kolommen, snap["cards"])
        self.assertEqual(kolommen, ["merged"])


if __name__ == "__main__":
    unittest.main()
