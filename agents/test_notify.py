# SPDX-License-Identifier: MIT
"""The push cooldown may DELAY a notification, never swallow it.

Measured 2026-09-18 on the live listener: two messages in #bouw six seconds
apart gave exactly one push, and the second surfaced only as "(+1 eerder)" on
the next message in that channel — four days later. These tests pin the rule
that came out of it: what the cooldown holds back, `flush` delivers.
"""
import unittest
from unittest import mock

import notify


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


if __name__ == "__main__":
    unittest.main()
