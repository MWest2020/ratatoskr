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
            turn = agent_turn.build({"bouwer": CFG}, "odin", FakeReg(), send, {},
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
