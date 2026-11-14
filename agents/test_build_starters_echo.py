# SPDX-License-Identifier: MIT
"""What the listener posts itself never comes back as a build, and an agent that
retries a refused `!build` is not answered again (build_starters.py).

Review of PR #242: relay.sender says False on a timeout even when the event was
published, so `OwnPosts` must remember a post before the send. And an odin
answer with `!sessie` on line 1 and `!build` on line 2 is posted with the
`!build` as its first line (the session marker is stripped, the build marker is
not, since it was not on line 1)."""
import os
import tempfile
import unittest
from unittest import mock

import agent_turn
import build
import build_starters
import providers
from test_build_starters import RoadFixture

ODIN_NPUB = build_starters.identities()["odin"]["npub"]


class FakeReg:
    cfg = {"types": {}}


class OwnPosts(unittest.TestCase):
    def test_a_failed_send_is_still_remembered(self):
        own = build_starters.OwnPosts(lambda *a: False)   # timeout, maybe published
        self.assertFalse(own("cid", "!build ratatoskr x", "n", ODIN_NPUB))
        self.assertTrue(own.seen("cid", ODIN_NPUB, "!build  ratatoskr x\n"))

    def test_keyed_on_channel_and_signer(self):
        own = build_starters.OwnPosts(lambda *a: True)
        own("cid", "!build ratatoskr x", "n", ODIN_NPUB)
        self.assertFalse(own.seen("other", ODIN_NPUB, "!build ratatoskr x"))
        self.assertFalse(own.seen("cid", "npub1someoneelse", "!build ratatoskr x"))


class Echo(RoadFixture, unittest.TestCase):
    def run_hub_turn(self, answer, send):
        cfg = {"system": "You are odin.", "nsec": "nsec1x", "npub": ODIN_NPUB,
               "channels": [], "provider": "claude-p"}

        def fake_run(provider, system, prompt, **k):
            return {"answer": answer, "model": "m", "cost": 0.0, "turns": 1,
                    "denials": [], "error": ""}
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(providers, "run", fake_run), \
                mock.patch("reporting.report_run"), \
                mock.patch("reporting.progress_poster", return_value=None):
            os.makedirs(os.path.join(root, "knowledge"))
            turn = agent_turn.build_turn({"odin": cfg}, "odin", FakeReg(), send, {}, {}, root,
                                         lambda *a, **k: None, log=lambda *a, **k: None,
                                         try_build=self.try_build)
            msgs = [{"pubkey": "pm", "content": "look at x", "id": "m1"}]
            return turn("odin", "escalatie", "cid", msgs, 0, "look at x", "mark", "m1",
                        "default")[1]

    def test_the_echo_of_an_odin_answer_does_not_build(self):
        posts = []
        own = build_starters.OwnPosts(lambda cid, text, *a: posts.append(text) or False)
        self.run_hub_turn("!sessie wordsworth look at x\n!build ratatoskr x", own)  # send "timed out"
        self.assertTrue(posts[0].startswith("!build ratatoskr x"))   # the route is real
        self.assertTrue(self.take("odin", posts[0], own_posts=own))  # handled, not chat
        self.assertEqual(self.argv, [])
        # Without the guard the same echo would have started a build.
        self.take("odin", posts[0], own_posts=build_starters.OwnPosts(lambda *a: True))
        self.assertEqual(len(self.argv), 1)


class Throttle(RoadFixture, unittest.TestCase):
    def test_the_same_refused_marker_is_dropped_for_ten_minutes(self):
        with mock.patch.object(build, "check", wraps=build.check) as chk:
            self.take("jarvis", "!build alma x")             # not on the factory's list
            self.assertIn("⛔", self.said[-1])
            said, checks = len(self.said), chk.call_count
            self.t[0] += 300
            self.assertTrue(self.take("jarvis", "!build alma x"))
            self.assertEqual((len(self.said), chk.call_count), (said, checks))  # no line, no gh
            self.assertIn("dropped", self.logged[-1])
            self.t[0] += build_starters.QUIET
            self.take("jarvis", "!build alma x")
            self.assertEqual(len(self.said), said + 1)        # asked again after the quiet

    def test_only_that_starter_and_that_marker(self):
        self.take("jarvis", "!build alma x")
        n = len(self.said)
        self.take("claude", "!build alma x")                  # another starter: answered
        self.take("jarvis", "!build alma y")                  # another marker: answered
        self.assertEqual(len(self.said), n + 2)

    def test_a_refusal_that_can_change_soon_is_always_answered(self):
        why = "no OpenSpec change `x` on main"             # the spec PR may merge in a minute
        with mock.patch.object(build, "check", return_value=(None, why)):
            self.take("jarvis", "!build ratatoskr x")
            self.take("jarvis", "!build ratatoskr x")
        self.assertEqual(sum("⛔" in s for s in self.said[-2:]), 2)
        self.assertEqual(self.refused, {})

    def test_a_started_build_is_not_throttled(self):
        self.take("claude", "!build ratatoskr x")
        self.assertEqual(self.refused, {})


if __name__ == "__main__":
    unittest.main()
