# SPDX-License-Identifier: MIT
"""The push cooldown may DELAY a notification, never swallow it.

Measured 2026-09-18 on the live listener: two messages in #bouw six seconds
apart gave exactly one push, and the second surfaced only as "(+1 eerder)" on
the next message in that channel — four days later. These tests pin the rule
that came out of it: what the cooldown holds back, `flush` delivers.
"""
import json
import os
import unittest
from unittest import mock

import notify

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(os.path.dirname(HERE), "chat", "testdata", "imeta-event.json")) as f:
    EVENT = json.load(f)   # the one recorded image event (gate 1.1); no second copy
IMAGE_BODY = "🖼 gate 1.1 imeta probe (#243) — 16x16 test image, deleted right after"


class TestShouldNotify(unittest.TestCase):
    def test_own_message_silent_channel_and_progress_do_not_notify(self):
        self.assertFalse(notify.should_notify("statistics", "odin", "x", "mark"))
        self.assertFalse(notify.should_notify("bouw", "mark", "x", "mark"))
        self.assertFalse(notify.should_notify("bouw", "odin", "⋯ bezig", "mark"))
        self.assertFalse(notify.should_notify("bouw", "odin", "   ", "mark"))

    def test_an_agent_answer_notifies(self):
        self.assertTrue(notify.should_notify("bouw", "bouwer", "klaar", "mark"))


class TestCooldown(unittest.TestCase):
    def setUp(self):
        notify._last.clear()
        self.addCleanup(notify._last.clear)
        p = mock.patch.object(notify, "_send", return_value=True)
        self.send = p.start()
        self.addCleanup(p.stop)

    def bodies(self):
        return [c.args[2] for c in self.send.call_args_list]

    def test_first_message_pushes(self):
        self.assertTrue(notify.push("bouw", "bouwer", "een"))
        self.assertEqual(self.bodies(), ["een"])

    def test_second_message_inside_the_cooldown_is_held_back(self):
        notify.push("bouw", "bouwer", "een")
        self.assertFalse(notify.push("bouw", "bouwer", "twee"))
        self.assertEqual(self.bodies(), ["een"])

    def test_flush_delivers_it_once_the_cooldown_has_expired(self):
        notify.push("bouw", "bouwer", "een")
        notify.push("bouw", "bouwer", "twee")
        self.assertEqual(notify.flush(), [])          # still inside the cooldown
        later = notify._last["bouw"][0] + notify.COOLDOWN + 1
        self.assertEqual(notify.flush(now=later), ["bouw"])
        self.assertEqual(self.bodies(), ["een", "twee"])

    def test_flush_is_idempotent(self):
        notify.push("bouw", "bouwer", "een")
        notify.push("bouw", "bouwer", "twee")
        later = notify._last["bouw"][0] + notify.COOLDOWN + 1
        notify.flush(now=later)
        self.assertEqual(notify.flush(now=later + notify.COOLDOWN + 1), [])
        self.assertEqual(len(self.bodies()), 2)

    def test_a_burst_keeps_the_newest_and_counts_the_rest(self):
        notify.push("bouw", "bouwer", "een")
        for n in ("twee", "drie", "vier"):
            notify.push("bouw", "bouwer", n)
        later = notify._last["bouw"][0] + notify.COOLDOWN + 1
        notify.flush(now=later)
        self.assertEqual(self.bodies(), ["een", "vier  (+2 eerder)"])

    def test_channels_have_their_own_cooldown(self):
        notify.push("bouw", "bouwer", "een")
        self.assertTrue(notify.push("review", "reviewer", "twee"))
        self.assertEqual(self.bodies(), ["een", "twee"])

    def test_a_long_message_is_shortened(self):
        notify.push("bouw", "bouwer", "x" * 300)
        self.assertEqual(len(self.bodies()[0]), 138)
        self.assertTrue(self.bodies()[0].endswith("…"))


class TestSendNamesItsFailure(unittest.TestCase):
    def test_a_sender_that_exits_non_zero_is_named_and_not_counted(self):
        r = mock.Mock(returncode=3, stdout="", stderr="geen subscriptions")
        with mock.patch.object(notify.subprocess, "run", return_value=r), \
             mock.patch("builtins.print") as pr:
            self.assertFalse(notify._send("bouw", "bouwer", "een"))
        self.assertIn("rc=3", pr.call_args.args[0])


class TestImagePush(unittest.TestCase):
    """The Web Push seam (AGENTS.md, silent chain 1): subprocess.run patched,
    not _send, so the real argv to push-notify.py is what is asserted."""

    def setUp(self):
        notify._last.clear()
        self.addCleanup(notify._last.clear)
        p = mock.patch.object(notify.subprocess, "run", return_value=mock.Mock(returncode=0))
        self.run_ = p.start()
        self.addCleanup(p.stop)

    def bodies(self):
        return [c.args[0][c.args[0].index("--body") + 1] for c in self.run_.call_args_list]

    def test_an_image_event_pushes_its_caption_behind_the_marker(self):
        self.assertTrue(notify.on_message("bouw", "odin", EVENT, "mark"))
        self.assertEqual(self.bodies(), [IMAGE_BODY])
        self.assertNotIn("![image]", self.bodies()[0])
        self.assertNotIn("/media/", self.bodies()[0])
        argv = self.run_.call_args.args[0]
        self.assertEqual(argv[argv.index("--url") + 1], "/#bouw")

    def test_an_image_held_by_the_cooldown_flushes_with_the_same_body(self):
        notify.on_message("bouw", "odin", {"content": "first"}, "mark")
        self.assertFalse(notify.on_message("bouw", "odin", EVENT, "mark"))   # held
        later = notify._last["bouw"][0] + notify.COOLDOWN + 1
        self.assertEqual(notify.flush(now=later), ["bouw"])
        self.assertEqual(self.bodies(), ["first", IMAGE_BODY])

    def test_a_message_without_an_image_is_unchanged(self):
        notify.on_message("bouw", "odin", {"content": "plain\ntext", "tags": [["h", "x"]]}, "mark")
        self.assertEqual(self.bodies(), ["plain text"])

    def test_an_image_without_a_caption_says_image(self):
        url = EVENT["tags"][1][1].split(" ", 1)[1]
        notify.on_message("bouw", "odin", dict(EVENT, content=f"![image]({url})"), "mark")
        self.assertEqual(self.bodies(), ["🖼 image"])

    def test_should_notify_still_filters(self):
        self.assertFalse(notify.on_message("statistics", "odin", EVENT, "mark"))
        self.assertFalse(notify.on_message("bouw", "mark", EVENT, "mark"))
        self.assertFalse(notify.on_message("bouw", "odin", {"content": "⋯ busy"}, "mark"))
        self.assertEqual(self.bodies(), [])

    def test_malformed_tags_give_the_plain_text_body(self):
        shapes = {"imeta string": ["imeta"], "imeta and int": ["imeta", 7], "None field": [["imeta", None]],
                  "string": "imeta", "dict": {"imeta": 1}}
        for name, tags in shapes.items():
            with self.subTest(name):
                notify._last.clear()
                notify.on_message("bouw", "odin", dict(EVENT, tags=tags), "mark")
        notify._last.clear()
        notify.on_message("bouw", "odin", {"content": EVENT["content"]}, "mark")   # tags missing
        plain = EVENT["content"].replace("\n", " ")[:137] + "…"
        self.assertEqual(self.bodies(), [plain] * 6)

    def test_an_imeta_that_raises_costs_the_marker_not_the_push(self):
        with mock.patch.object(notify.imeta, "from_tags", side_effect=TypeError("boom")), \
             mock.patch("builtins.print") as pr:
            self.assertTrue(notify.on_message("bouw", "odin", EVENT, "mark"))
        self.assertIn("[listener] notify: image tags unreadable (boom)", pr.call_args.args[0])
        self.assertEqual(len(self.bodies()), 1)
        self.assertTrue(self.bodies()[0].startswith("gate 1.1 imeta probe"))


class TestListenerSeam(unittest.TestCase):
    def test_the_listener_hands_the_whole_event_to_notify(self):
        with open(os.path.join(HERE, "listener.py")) as fh:
            src = fh.read()
        self.assertEqual(src.count("notify.on_message(cname, writer, m, ME_NAME)"), 1)
        self.assertNotIn("notify.push(", src)
        self.assertNotIn("notify.should_notify(", src)


if __name__ == "__main__":
    unittest.main()
