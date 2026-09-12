# SPDX-License-Identifier: EUPL-1.2
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
import board_sources  # noqa: E402

COLUMNS = [{"key": "proposal", "title": "voorstel", "stale_days": 14},
           {"key": "building", "title": "bouwen", "stale_days": 3},
           {"key": "review", "title": "review", "stale_days": 2},
           {"key": "merged", "title": "gemerged", "stale_days": 0}]


class Column(unittest.TestCase):
    def test_merged_wins(self):
        self.assertEqual(board_model.pr_column({"merged": True, "draft": True}), "merged")

    def test_draft_is_building(self):
        self.assertEqual(board_model.pr_column({"draft": True}), "building")

    def test_open_non_draft_is_waiting_on_a_human(self):
        """In this flow an open PR stays put until someone merges it."""
        self.assertEqual(board_model.pr_column({"draft": False}), "review")

    def test_missing_draft_flag_is_review(self):
        self.assertEqual(board_model.pr_column({}), "review")


class Age(unittest.TestCase):
    def test_days(self):
        now = 1000 * board_model.DAY
        self.assertAlmostEqual(board_model.age_days(now - 2 * board_model.DAY, now), 2.0)

    def test_never_negative(self):
        """A clock running behind must not produce a card from the future."""
        now = 100.0
        self.assertEqual(board_model.age_days(now + 5000, now), 0.0)

    def test_missing_timestamp_is_zero(self):
        self.assertEqual(board_model.age_days(None, 123.0), 0.0)


class Stale(unittest.TestCase):
    def test_over_threshold(self):
        self.assertTrue(board_model.is_stale({"column": "review", "age_days": 3}, COLUMNS))

    def test_under_threshold(self):
        self.assertFalse(board_model.is_stale({"column": "review", "age_days": 1}, COLUMNS))

    def test_zero_threshold_is_never_stale(self):
        """The exit column: anything may rest there."""
        self.assertFalse(board_model.is_stale({"column": "merged", "age_days": 999}, COLUMNS))

    def test_unknown_column_is_never_stale(self):
        self.assertFalse(board_model.is_stale({"column": "x", "age_days": 999}, COLUMNS))


class Ignore(unittest.TestCase):
    def test_ignored_repo_is_dropped(self):
        """A PR on a repo you no longer work on is the oldest card, and therefore
        shouts loudest every day. Not every open thing is work."""
        rows = [{"repository": {"name": "oud-project"}, "number": 1, "title": "x",
                 "updatedAt": "2026-01-01T00:00:00Z", "url": "", "isDraft": False,
                 "author": {"login": "a"}}]
        board_sources.gh_json = lambda args: rows if "--state=open" in args else []
        self.assertEqual(board_sources.pr_cards("owner", 3, time.time(), {"oud-project"}), [])
        self.assertEqual(len(board_sources.pr_cards("owner", 3, time.time(), set())), 1)


class Summary(unittest.TestCase):
    def test_counts_and_stale(self):
        cards = [{"column": "review", "stale": True}, {"column": "review", "stale": False},
                 {"column": "building", "stale": False}]
        s = {c["key"]: c for c in board_model.summarise(cards, COLUMNS)}
        self.assertEqual((s["review"]["count"], s["review"]["stale"]), (2, 1))
        self.assertEqual(s["proposal"]["count"], 0)

    def test_every_column_is_present_even_when_empty(self):
        """An empty column must be visibly empty, not absent."""
        self.assertEqual(len(board_model.summarise([], COLUMNS)), 4)


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


class Snapshot(unittest.TestCase):
    def test_failing_source_becomes_an_error_not_silence(self):
        """Silently showing nothing is indistinguishable from 'nothing to do'."""
        empty = os.path.join(tempfile.mkdtemp(), "geen-cache.json")
        cfg = {"columns": COLUMNS,
               "sources": {"openspec_glob": "/bestaat/niet/*", "github_owner": "x",
                           "session_runs": "/bestaat/niet", "merged_days": 3,
                           "pr_cache": empty, "pr_cache_seconds": 600}}
        board_sources.gh_json = lambda args: (_ for _ in ()).throw(RuntimeError("gh weg"))
        snap = board.build(cfg, now=1000.0)
        self.assertTrue(snap["errors"])
        self.assertIn("gh weg", snap["errors"][0])
        self.assertEqual(snap["cards"], [])

    def test_stale_cache_is_used_but_announced(self):
        """An old cache is better than an empty board — as long as the board says
        it is old. Silently showing old PRs is the false clear in disguise."""
        cache = os.path.join(tempfile.mkdtemp(), "prs.json")
        with open(cache, "w") as f:
            json.dump({"at": 0, "cards": [{"column": "review", "age_days": 1}]}, f)
        cfg = {"columns": COLUMNS,
               "sources": {"openspec_glob": "/bestaat/niet/*", "github_owner": "x",
                           "session_runs": "/bestaat/niet", "merged_days": 3,
                           "pr_cache": cache, "pr_cache_seconds": 1}}
        board_sources.gh_json = lambda args: (_ for _ in ()).throw(RuntimeError("gh weg"))
        snap = board.build(cfg, now=1000.0)
        self.assertEqual(len(snap["cards"]), 1)
        self.assertIn("niet ververst", snap["errors"][0])

    def test_fresh_cache_skips_github(self):
        """This is what makes a running session visible: the PR side need not be
        fetched again every two minutes."""
        cache = os.path.join(tempfile.mkdtemp(), "prs.json")
        with open(cache, "w") as f:
            json.dump({"at": 999.0, "cards": []}, f)
        cfg = {"columns": COLUMNS,
               "sources": {"openspec_glob": "/bestaat/niet/*", "github_owner": "x",
                           "session_runs": "/bestaat/niet", "merged_days": 3,
                           "pr_cache": cache, "pr_cache_seconds": 600}}
        def boom(args):
            raise AssertionError("gh should not have been called")
        board_sources.gh_json = boom
        self.assertEqual(board.build(cfg, now=1000.0)["errors"], [])


if __name__ == "__main__":
    unittest.main()


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
