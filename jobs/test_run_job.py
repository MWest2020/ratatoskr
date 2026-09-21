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
import sys
import unittest

import yaml

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


class TestStilleStoring(unittest.TestCase):
    """Op 2026-09-21 sneuvelden alle vier de terugkerende jobs om 08:00 op een
    claude-installatie die niet uitvoerbaar was. In de kanalen stond niets; de
    storing kwam aan het licht doordat Mark om 15:30 vroeg "no standup this
    morning?". Afwezigheid leest als "niets te melden"."""

    def _job(self):
        return {"channel": "kanaal-1", "identity": "odin", "prompt": "x"}

    def test_de_melding_gaat_naar_het_kanaal_van_de_job(self):
        gezien = {}

        def nep(args, env, tekst, npub, wat, name):
            gezien.update(args=args, tekst=tekst, wat=wat)
            return True

        oud, run_job.stuur = run_job.stuur, nep
        try:
            ok = run_job.meld_storing("standup", self._job(),
                                      "claude niet te starten", {}, "npub1")
        finally:
            run_job.stuur = oud
        self.assertTrue(ok)
        self.assertIn("kanaal-1", gezien["args"])
        self.assertIn("standup", gezien["tekst"])
        self.assertIn("claude niet te starten", gezien["tekst"])

    def test_een_weigerende_relay_maakt_er_geen_succes_van(self):
        """Anders meldt het journaal "storing gemeld" terwijl er niets staat."""
        class Nep:
            returncode = 1
            stderr = "relay weigert"

        oud, run_job.subprocess.run = run_job.subprocess.run, lambda *a, **k: Nep()
        try:
            ok = run_job.stuur(["buzz"], {}, "tekst", "", "posten", "standup")
        finally:
            run_job.subprocess.run = oud
        self.assertFalse(ok)

    def test_main_meldt_een_claude_die_niet_te_starten_is(self):
        """Het echte geval van 2026-09-21, van buitenaf: een CLAUDE_BIN die
        bestaat maar niet uitvoerbaar is. Vóór deze wijziging viel de job om met
        een PermissionError en bleef het kanaal leeg."""
        import tempfile
        # Expliciet deze job: zijn context_cmd is een lokale `git log`. De
        # andere jobs lezen de relay of alle clones, en een toets hoort niet aan
        # het netwerk te hangen om een PermissionError te bewijzen.
        naam = "news_from_zettelkast"
        with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as f:
            f.write(b"#!/bin/sh\necho x\n")       # bestaat wel, uitvoerbaar niet
        os.chmod(f.name, 0o644)

        gemeld = {}
        oud_bin, run_job.CLAUDE = run_job.CLAUDE, f.name
        oud_meld, run_job.meld_storing = run_job.meld_storing, \
            lambda name, job, reden, env, npub: gemeld.update(reden=reden) or True
        oud_argv, sys.argv = sys.argv, ["run-job.py", naam]
        os.environ["NSEC_ORCHESTRATOR"] = "nsec-test"
        os.environ["NSEC_ODIN"] = "nsec-test"
        try:
            run_job.main()
        finally:
            run_job.CLAUDE, run_job.meld_storing = oud_bin, oud_meld
            sys.argv = oud_argv
            os.unlink(f.name)
        self.assertIn("niet te starten", gemeld.get("reden", ""))
