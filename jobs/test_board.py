# SPDX-License-Identifier: EUPL-1.2
"""Tests voor het werk-overzicht. Alleen de PURE kant: kolomkeuze, ouderdom en
muf-zijn. Die bepalen wat het bord zegt, en die wil je kunnen testen zonder
GitHub en zonder klok.

Draaien: cd jobs && python3 -m unittest test_board
"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board  # noqa: E402

COLUMNS = [{"key": "proposal", "title": "voorstel", "stale_days": 14},
           {"key": "building", "title": "bouwen", "stale_days": 3},
           {"key": "review", "title": "review", "stale_days": 2},
           {"key": "merged", "title": "gemerged", "stale_days": 0}]


class Column(unittest.TestCase):
    def test_merged_wins(self):
        self.assertEqual(board.pr_column({"merged": True, "draft": True}), "merged")

    def test_draft_is_building(self):
        self.assertEqual(board.pr_column({"draft": True}), "building")

    def test_open_non_draft_is_waiting_on_a_human(self):
        """In deze flow blijft een open PR staan tot iemand 'm merget."""
        self.assertEqual(board.pr_column({"draft": False}), "review")

    def test_missing_draft_flag_is_review(self):
        self.assertEqual(board.pr_column({}), "review")


class Age(unittest.TestCase):
    def test_days(self):
        now = 1000 * board.DAY
        self.assertAlmostEqual(board.age_days(now - 2 * board.DAY, now), 2.0)

    def test_never_negative(self):
        """Een klok die achterloopt mag geen kaart uit de toekomst opleveren."""
        now = 100.0
        self.assertEqual(board.age_days(now + 5000, now), 0.0)

    def test_missing_timestamp_is_zero(self):
        self.assertEqual(board.age_days(None, 123.0), 0.0)


class Stale(unittest.TestCase):
    def test_over_threshold(self):
        self.assertTrue(board.is_stale({"column": "review", "age_days": 3}, COLUMNS))

    def test_under_threshold(self):
        self.assertFalse(board.is_stale({"column": "review", "age_days": 1}, COLUMNS))

    def test_zero_threshold_is_never_stale(self):
        """De uitgangskolom: daar mag alles liggen."""
        self.assertFalse(board.is_stale({"column": "merged", "age_days": 999}, COLUMNS))

    def test_unknown_column_is_never_stale(self):
        self.assertFalse(board.is_stale({"column": "x", "age_days": 999}, COLUMNS))


class Summary(unittest.TestCase):
    def test_counts_and_stale(self):
        cards = [{"column": "review", "stale": True}, {"column": "review", "stale": False},
                 {"column": "building", "stale": False}]
        s = {c["key"]: c for c in board.summarise(cards, COLUMNS)}
        self.assertEqual((s["review"]["count"], s["review"]["stale"]), (2, 1))
        self.assertEqual(s["proposal"]["count"], 0)

    def test_every_column_is_present_even_when_empty(self):
        """Een lege kolom moet zichtbaar leeg zijn, niet afwezig."""
        self.assertEqual(len(board.summarise([], COLUMNS)), 4)


class OpenspecCards(unittest.TestCase):
    def test_archive_is_skipped(self):
        d = tempfile.mkdtemp()
        levend = os.path.join(d, "home", "agent", "repo", "openspec", "changes", "nieuw")
        dood = os.path.join(d, "home", "agent", "repo", "openspec", "changes", "archive", "oud")
        for p in (levend, dood):
            os.makedirs(p)
            open(os.path.join(p, "proposal.md"), "w").write("x")
        got = board.openspec_cards(os.path.join(d, "home/agent/*/openspec/changes/*/proposal.md"),
                                   time.time())
        self.assertEqual([c["title"] for c in got], ["nieuw"])


class Snapshot(unittest.TestCase):
    def test_failing_source_becomes_an_error_not_silence(self):
        """Stil niets tonen is niet te onderscheiden van 'er is niets te doen'."""
        cfg = {"columns": COLUMNS,
               "sources": {"openspec_glob": "/bestaat/niet/*", "github_owner": "x",
                           "session_runs": "/bestaat/niet", "merged_days": 3}}
        board.gh_json = lambda args: (_ for _ in ()).throw(RuntimeError("gh weg"))
        snap = board.build(cfg, now=1000.0)
        self.assertTrue(snap["errors"])
        self.assertIn("gh weg", snap["errors"][0])
        self.assertEqual(snap["cards"], [])


if __name__ == "__main__":
    unittest.main()
