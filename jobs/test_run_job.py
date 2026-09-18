# SPDX-License-Identifier: MIT
"""The recurring jobs run `claude -p` daily and cost money, but never showed up
in #statistics — only chat-agent turns did. That is what made the channel look
as if it reported at random (Mark, 2026-09-18).

These tests pin the two halves of the fix: reading the cost out of the JSON, and
falling back on the raw text when that is not JSON — because a changed output
format of the CLI may cost the stats line, never the digest itself.
"""
import importlib.util
import json
import os
import unittest

os.environ.setdefault("BUZZ_RELAY_URL", "ws://test")
_spec = importlib.util.spec_from_file_location(
    "run_job", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run-job.py"))
run_job = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_job)


class TestAntwoordEnKosten(unittest.TestCase):
    def test_json_gives_answer_and_stats(self):
        # Field names measured 2026-09-18 against the installed claude CLI.
        out = json.dumps({"result": "🗞️ digest", "num_turns": 2,
                          "total_cost_usd": 0.1234,
                          "modelUsage": {"claude-sonnet-5": {"inputTokens": 10}}})
        answer, stats = run_job.antwoord_en_kosten(out)
        self.assertEqual(answer, "🗞️ digest")
        self.assertEqual(stats, {"model": "claude-sonnet-5", "turns": 2, "cost": 0.1234})

    def test_plain_text_still_yields_the_digest(self):
        answer, stats = run_job.antwoord_en_kosten("  gewone tekst  ")
        self.assertEqual(answer, "gewone tekst")
        self.assertIsNone(stats)   # no stats line, but the job does post

    def test_json_without_the_fields_does_not_crash(self):
        answer, stats = run_job.antwoord_en_kosten(json.dumps({"result": "x"}))
        self.assertEqual(stats, {"model": "?", "turns": 0, "cost": 0.0})

    def test_empty_and_non_object_json(self):
        self.assertEqual(run_job.antwoord_en_kosten(""), ("", None))
        self.assertEqual(run_job.antwoord_en_kosten("[1,2]"), ("[1,2]", None))
        self.assertEqual(run_job.antwoord_en_kosten(None), ("", None))


class TestPostStatistieken(unittest.TestCase):
    def test_without_stats_nothing_is_sent(self):
        calls = []
        orig = run_job.subprocess.run
        run_job.subprocess.run = lambda *a, **k: calls.append(a)
        try:
            run_job.post_statistieken("standup", {"identity": "orchestrator"},
                                      None, {}, "npub1x")
        finally:
            run_job.subprocess.run = orig
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
