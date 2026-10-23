# SPDX-License-Identifier: MIT
"""The turn that left the poll loop (shared-room): it still runs the model with
the agent's own limits, posts the answer, and now also takes a room context, a
suffix and a marker filter. The model is faked; prompts and routing are real."""
import os
import tempfile
import unittest
from unittest import mock

import agent_turn
import providers


class FakeReg:
    cfg = {"types": {}}


CFG = {"system": "You are bouwer.", "model": "sonnet", "allow": ["Read"], "deny": ["Bash"],
       "routes": [], "nsec": "nsec1x", "npub": "npub1x", "provider": "claude-p"}


class Turn(unittest.TestCase):
    def run_one(self, answer, **kw):
        sent, seen = [], {}

        def fake_run(provider, system, prompt, **k):
            seen.update(system=system, prompt=prompt, **k)
            return {"answer": answer, "model": "claude-sonnet-5", "cost": 0.0,
                    "turns": 1, "denials": [], "error": ""}

        def send(cid, text, nsec, npub):
            sent.append((cid, text, npub))
            return True
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(providers, "run", fake_run), \
             mock.patch("reporting.report_run"), \
             mock.patch("reporting.progress_poster", return_value=None):
            os.makedirs(os.path.join(root, "knowledge"), exist_ok=True)
            turn = agent_turn.build_turn({"bouwer": CFG}, "odin", FakeReg(), send, {},
                                    {}, root, lambda *a, **k: None, log=lambda *a, **k: None)
            msgs = [{"pubkey": "pm", "content": "hello", "id": "m1"}]
            out = turn("bouwer", "werkplaats", "cid", msgs, 0, "hello", "mark", "m1",
                       "triage", **kw)
        return out, sent, seen

    def test_the_agents_own_limits_reach_the_model(self):
        _, _, seen = self.run_one("ok")
        self.assertTrue(seen["system"].startswith("You are bouwer."))
        self.assertEqual((seen["model"], seen["allow"], seen["deny"]),
                         ("sonnet", ["Read"], ["Bash"]))

    def test_room_context_suffix_and_filter(self):
        (ans, posted), sent, seen = self.run_one(
            "the plan\n!done planned", extra="SHARED ROOM ctx", suffix="\n\n· ratatoskr#7",
            clean=lambda t: t.replace("\n!done planned", ""))
        self.assertTrue(seen["prompt"].startswith("SHARED ROOM ctx"))
        self.assertEqual(sent, [("cid", "the plan\n\n· ratatoskr#7", "npub1x")])
        self.assertEqual((ans, posted), ("the plan\n!done planned", "the plan"))

    def test_without_room_arguments_it_behaves_as_before(self):
        (ans, posted), sent, _ = self.run_one("plain answer")
        self.assertEqual(sent, [("cid", "plain answer", "npub1x")])
        self.assertEqual(posted, "plain answer")


if __name__ == "__main__":
    unittest.main()


class Markers(unittest.TestCase):
    """2026-10-23: the prompt said LAST line, the listener reads the FIRST; odin's
    `!sessie` was dropped without a word while it told Mark a session started."""

    def test_the_prompt_says_first_line(self):
        import prompts
        cfg = {"types": {"wordsworth": {"starters": ["mark", "odin"], "description": "wordsworth"}}}
        clause = prompts.session_clause(cfg, "odin", "mark")
        self.assertIn("FIRST line", clause)
        self.assertNotIn("LAST line", clause)

    def test_a_marker_on_the_last_line_is_said_not_swallowed(self):
        ans = "I'll start a session.\n\n!sessie wordsworth Can it ingest a publication?"
        note = agent_turn.misplaced(ans)
        self.assertIn("`!sessie` was not on the first line", note)
        self.assertEqual(agent_turn.misplaced("!sessie wordsworth go\nok"), "")
        self.assertEqual(agent_turn.misplaced("no markers here"), "")

    def test_the_turn_posts_the_note(self):
        (_, posted), sent, _ = Turn().run_one("Starting.\n!build wordsworth x")
        self.assertIn("was not on the first line", sent[0][1])


class FollowUp(unittest.TestCase):
    def test_a_follow_up_cannot_start_a_session(self):
        started = []
        sent = []

        def fake_run(provider, system, prompt, **k):
            return {"answer": "!sessie research more\nOn it.", "error": ""}
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(providers, "run", fake_run), \
             mock.patch("reporting.report_run"), \
             mock.patch("reporting.progress_poster", return_value=None):
            os.makedirs(os.path.join(root, "knowledge"), exist_ok=True)
            turn = agent_turn.build_turn({"bouwer": CFG}, "odin", FakeReg(),
                                         lambda cid, t, *a: sent.append(t) or True, {}, {}, root,
                                         lambda *a, **k: started.append(a),
                                         log=lambda *a, **k: None)
            msgs = [{"pubkey": "pm", "content": "x", "id": "m1"}]
            turn("bouwer", "general", "cid", msgs, 0, "x", "mark", "m1", "session-done",
                 followup=True)
        self.assertEqual(started, [])
        self.assertTrue(any("no new session from a follow-up turn" in t for t in sent))
