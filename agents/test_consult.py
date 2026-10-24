# SPDX-License-Identifier: MIT
"""`!consult` (Mark, 2026-10-23): the hub gives other agents a turn itself, in
the channel where Mark asked. Through the real agent_turn, with the model faked:
who answers, in what order, with what, and what never happens (chains, more
than two, a quote acting)."""
import os
import tempfile
import unittest
from unittest import mock

import agent_turn
import consult
import providers


class FakeReg:
    cfg = {"types": {}}


def cfg(name):
    return {"system": f"You are {name}.", "model": "sonnet", "allow": [], "deny": [],
            "routes": [], "nsec": name, "npub": name, "provider": "claude-p",
            "channels": ["general"]}


AGENTS = {h: cfg(h) for h in ("odin", "architect", "reviewer", "bouwer")}


class Consult(unittest.TestCase):
    def run_hub(self, answers, may_speak=lambda h, c, i: True):
        sent, prompts = [], []

        def fake_run(provider, system, prompt, **k):
            who = system.split("You are ", 1)[1].split(".", 1)[0]
            prompts.append((who, prompt))
            a = answers[who]
            return {"answer": a.pop(0) if isinstance(a, list) else a, "error": ""}
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(providers, "run", fake_run), \
             mock.patch("reporting.report_run"), \
             mock.patch("reporting.progress_poster", return_value=None):
            os.makedirs(os.path.join(root, "knowledge"), exist_ok=True)
            turn = agent_turn.build_turn(AGENTS, "odin", FakeReg(),
                                         lambda cid, t, nsec, npub: sent.append((npub, t)) or True,
                                         {}, {}, root, lambda *a, **k: None,
                                         log=lambda *a, **k: None, may_speak=may_speak)
            msgs = [{"pubkey": "pm", "content": "is this an MVP?", "id": "m1"}]
            turn("odin", "general", "cid", msgs, 0, "is this an MVP?", "mark", "m1", "mention")
        return sent, prompts

    def test_two_agents_answer_under_their_own_name_after_odin(self):
        sent, prompts = self.run_hub({
            "odin": "!consult architect,reviewer Is one publication end to end an MVP?\nAsking.",
            "architect": "Smallest path: ingest, pseudonymise, search.",
            "reviewer": "Judge PII recall on one document."})
        self.assertEqual([who for who, _ in sent][:3], ["odin", "architect", "reviewer"])
        self.assertEqual(sent[0][1], "Asking.")              # the marker is not posted
        arch = dict(prompts)["architect"]
        self.assertIn("Is one publication end to end an MVP?", arch)
        self.assertIn("is this an MVP?", arch)                # Mark's own message comes along

    def test_no_chains(self):
        sent, prompts = self.run_hub({
            "odin": "!consult architect ask bouwer",
            "architect": "!consult bouwer go on", "bouwer": "should never run"})
        self.assertNotIn("bouwer", [who for who, _ in prompts])

    def test_at_most_two_and_refusals_are_said(self):
        sent, prompts = self.run_hub({
            "odin": "!consult architect,reviewer,bouwer,odin,ghost q",
            "architect": "a", "reviewer": "r", "bouwer": "b"})
        self.assertEqual([w for w, _ in prompts][:3], ["odin", "architect", "reviewer"])
        note = next(t for who, t in sent if t.startswith("⚠ not consulted"))
        for why in ("bouwer: at most 2", "odin is not an agent to consult",
                    "ghost is not an agent to consult"):
            self.assertIn(why, note)

    def test_an_agent_that_cannot_speak_here_is_not_consulted(self):
        sent, prompts = self.run_hub({"odin": "!consult architect q", "architect": "a"},
                                     may_speak=lambda h, c, i: h != "architect")
        self.assertEqual([w for w, _ in prompts], ["odin"])
        self.assertIn("architect cannot speak in this channel", sent[-1][1])

    def test_only_the_first_line(self):
        self.assertIsNone(consult.read_marker("quote:\n!consult architect q"))
        self.assertEqual(consult.read_marker("!consult architect,reviewer why?"),
                         (["architect", "reviewer"], "why?"))

    def test_only_the_hub_is_told(self):
        self.assertEqual(consult.clause("architect", "odin"), "")
        self.assertIn("!consult", consult.clause("odin", "odin"))



class ConsultFollowUp(Consult):
    """2026-10-23: odin announced its next step after a consult and was never
    woken to take it. Now it gets one turn with the answers, and no more."""

    def test_the_hub_acts_on_the_answers_once(self):
        sent, prompts = self.run_hub({
            "odin": ["!consult architect,reviewer Is the plan right?\nAsking.",
                     "!consult architect again?\nOpening the issue."],
            "architect": "Right, with a manifest.", "reviewer": "Go, with a provenance test."})
        self.assertEqual([w for w, _ in prompts], ["odin", "architect", "reviewer", "odin"])
        last = prompts[-1][1]
        self.assertIn("**architect:** Right, with a manifest.", last)
        self.assertIn("**reviewer:** Go, with a provenance test.", last)
        self.assertIn("is this an MVP?", last)
        self.assertIn("⚠ no consult from a follow-up turn", sent[-1][1])

    def test_no_answers_no_follow_up(self):
        sent, prompts = self.run_hub({"odin": "!consult architect q", "architect": ""})
        self.assertEqual([w for w, _ in prompts], ["odin", "architect"])


class KeepGoing(Consult):
    def test_only_the_hub_is_told_to_keep_going(self):
        seen = {}
        import providers as pv

        def fake_run(provider, system, prompt, **k):
            who = system.split("You are ", 1)[1].split(".", 1)[0]
            seen[who] = "Keep working until the assignment is done" in system
            return {"answer": "!consult architect q" if who == "odin" else "a", "error": ""}
        import os
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as root, mock.patch.object(pv, "run", fake_run), \
                mock.patch("reporting.report_run"), \
                mock.patch("reporting.progress_poster", return_value=None):
            os.makedirs(os.path.join(root, "knowledge"), exist_ok=True)
            turn = agent_turn.build_turn(AGENTS, "odin", FakeReg(), lambda *a: True, {}, {}, root,
                                         lambda *a, **k: None, log=lambda *a, **k: None)
            turn("odin", "general", "cid", [{"pubkey": "pm", "content": "go", "id": "m1"}], 0,
                 "go", "mark", "m1", "mention")
        self.assertTrue(seen["odin"])
        self.assertFalse(seen["architect"])


if __name__ == "__main__":
    unittest.main()
