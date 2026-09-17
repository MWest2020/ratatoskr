# SPDX-License-Identifier: MIT
"""Offline tests for `providers.py` (which model did the work).
Run from agents/: `python3 -m unittest test_providers` (agents/ has no
__init__.py and the modules use top-level imports, so the package path does not
work).
"""
import unittest

import providers


class ModelReportingTest(unittest.TestCase):
    """The stats line is the only place you can read whether the declared model is
    enforced. It took the FIRST key from modelUsage; a run touching several models
    then named an arbitrary one. Observed 2026-09-07: odin was reported as haiku
    while the handbook declares sonnet."""

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
        # cache tokens are often by far the biggest item; comparing inputTokens
        # alone would point at the wrong model.
        usage = {"a": {"inputTokens": 5}, "b": {"inputTokens": 1, "cacheReadInputTokens": 9000}}
        self.assertEqual(providers.main_model(usage, None), "b")

    def test_costs_do_not_count_as_tokens(self):
        usage = {"a": {"inputTokens": 10}, "b": {"costUSD": 9999}}
        self.assertEqual(providers.main_model(usage, None), "a")

    def test_family_match(self):
        self.assertTrue(providers.model_matches("sonnet", "claude-sonnet-5"))
        self.assertTrue(providers.model_matches("haiku", "claude-haiku-4-5-20251001"))
        self.assertFalse(providers.model_matches("sonnet", "claude-haiku-4-5"))
        self.assertTrue(providers.model_matches("", "wat dan ook"))   # nothing requested


if __name__ == "__main__":
    unittest.main()
