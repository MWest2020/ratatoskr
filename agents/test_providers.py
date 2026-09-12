# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor `providers.py` (welk model deed het werk).
Draaien vanuit agents/: `python3 -m unittest test_providers` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
"""
import unittest

import providers


class ModelReportingTest(unittest.TestCase):
    """De statistiekregel is het enige waarop je kunt aflezen of het gedeclareerde
    model afgedwongen wordt. Hij nam de EERSTE sleutel uit modelUsage; een run die
    meerdere modellen aanraakt noemde dan willekeurig één. Waargenomen 2026-09-07:
    odin werd als haiku gerapporteerd terwijl de handbook sonnet declareert."""

    def u(self, **kv):
        return {m: {"inputTokens": i, "outputTokens": 1} for m, i in kv.items()}

    def test_model_with_the_most_tokens_wins(self):
        usage = {"claude-haiku-4-5": {"inputTokens": 3, "outputTokens": 1},
                 "claude-sonnet-5": {"inputTokens": 900, "outputTokens": 400}}
        self.assertEqual(providers.main_model(usage, "sonnet"), "claude-sonnet-5")

    def test_order_in_the_map_does_not_matter(self):
        a = {"claude-haiku-4-5": {"inputTokens": 1}, "claude-sonnet-5": {"inputTokens": 99}}
        b = {"claude-sonnet-5": {"inputTokens": 99}, "claude-haiku-4-5": {"inputTokens": 1}}
        self.assertEqual(providers.main_model(a, "sonnet"), providers.main_model(b, "sonnet"))

    def test_without_usage_it_falls_back_to_what_was_requested(self):
        for empty in (None, {}, "geen dict"):
            self.assertEqual(providers.main_model(empty, "sonnet"), "sonnet")

    def test_all_token_fields_count(self):
        # cache-tokens zijn vaak veruit de grootste post; alleen inputTokens
        # vergelijken zou het verkeerde model aanwijzen.
        usage = {"a": {"inputTokens": 5}, "b": {"inputTokens": 1, "cacheReadInputTokens": 9000}}
        self.assertEqual(providers.main_model(usage, None), "b")

    def test_costs_do_not_count_as_tokens(self):
        usage = {"a": {"inputTokens": 10}, "b": {"costUSD": 9999}}
        self.assertEqual(providers.main_model(usage, None), "a")

    def test_family_match(self):
        self.assertTrue(providers.model_matches("sonnet", "claude-sonnet-5"))
        self.assertTrue(providers.model_matches("haiku", "claude-haiku-4-5-20251001"))
        self.assertFalse(providers.model_matches("sonnet", "claude-haiku-4-5"))
        self.assertTrue(providers.model_matches("", "wat dan ook"))   # niets gevraagd


if __name__ == "__main__":
    unittest.main()
