# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor `providers.py` (welk model deed het werk).
Draaien vanuit agents/: `python3 -m unittest test_providers` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
"""
import unittest

import providers


class ModelRapportageTest(unittest.TestCase):
    """De statistiekregel is het enige waarop je kunt aflezen of het gedeclareerde
    model afgedwongen wordt. Hij nam de EERSTE sleutel uit modelUsage; een run die
    meerdere modellen aanraakt noemde dan willekeurig één. Waargenomen 2026-09-07:
    odin werd als haiku gerapporteerd terwijl de handbook sonnet declareert."""

    def u(self, **kv):
        return {m: {"inputTokens": i, "outputTokens": 1} for m, i in kv.items()}

    def test_model_met_de_meeste_tokens_wint(self):
        usage = {"claude-haiku-4-5": {"inputTokens": 3, "outputTokens": 1},
                 "claude-sonnet-5": {"inputTokens": 900, "outputTokens": 400}}
        self.assertEqual(providers.main_model(usage, "sonnet"), "claude-sonnet-5")

    def test_volgorde_in_de_map_doet_er_niet_toe(self):
        a = {"claude-haiku-4-5": {"inputTokens": 1}, "claude-sonnet-5": {"inputTokens": 99}}
        b = {"claude-sonnet-5": {"inputTokens": 99}, "claude-haiku-4-5": {"inputTokens": 1}}
        self.assertEqual(providers.main_model(a, "sonnet"), providers.main_model(b, "sonnet"))

    def test_zonder_usage_valt_het_terug_op_wat_gevraagd_is(self):
        for leeg in (None, {}, "geen dict"):
            self.assertEqual(providers.main_model(leeg, "sonnet"), "sonnet")

    def test_alle_token_velden_tellen_mee(self):
        # cache-tokens zijn vaak veruit de grootste post; alleen inputTokens
        # vergelijken zou het verkeerde model aanwijzen.
        usage = {"a": {"inputTokens": 5}, "b": {"inputTokens": 1, "cacheReadInputTokens": 9000}}
        self.assertEqual(providers.main_model(usage, None), "b")

    def test_kosten_tellen_niet_mee_als_tokens(self):
        usage = {"a": {"inputTokens": 10}, "b": {"costUSD": 9999}}
        self.assertEqual(providers.main_model(usage, None), "a")

    def test_familie_match(self):
        self.assertTrue(providers.model_klopt("sonnet", "claude-sonnet-5"))
        self.assertTrue(providers.model_klopt("haiku", "claude-haiku-4-5-20251001"))
        self.assertFalse(providers.model_klopt("sonnet", "claude-haiku-4-5"))
        self.assertTrue(providers.model_klopt("", "wat dan ook"))   # niets gevraagd


if __name__ == "__main__":
    unittest.main()
