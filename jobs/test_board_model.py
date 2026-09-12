# SPDX-License-Identifier: EUPL-1.2
"""Tests voor de PURE kern van het werk-overzicht: kolom, ouderdom, muf,
samenvatting. Die bepalen wat het bord zegt, en die wil je kunnen testen zonder
GitHub en zonder klok.

De bronnen (clones, GitHub, sessies) staan in test_board.py — dezelfde splitsing
als in de code.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_model  # noqa: E402

COLUMNS = [{"key": "proposal", "title": "proposal", "stale_days": 14},
           {"key": "building", "title": "building", "stale_days": 3},
           {"key": "review", "title": "review", "stale_days": 2},
           {"key": "merged", "title": "merged", "stale_days": 0}]


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


if __name__ == "__main__":
    unittest.main()
