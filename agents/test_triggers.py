# SPDX-License-Identifier: MIT
"""The order of the three triggers, and the fact that it IS an order.

A unit test per trigger would pass while the bug that matters -- a weaker rule
winning over a stronger one -- goes unnoticed. These tests assert precedence.

Run with: cd agents && python3 -m unittest test_triggers
"""
import unittest

import triggers

AGENTS = {
    "odin": {"channels": ["general"]},
    "architect": {"channels": ["architectuur"]},
}
PUB2NAME = {"pub-odin": "odin", "pub-architect": "architect"}


def msg(pubkey):
    return {"pubkey": pubkey, "content": "..."}


def pick(text, earlier=(), cname="general", default=None, mentions=(), scope=None):
    return triggers.pick(
        text, list(earlier), cname, AGENTS, PUB2NAME,
        (lambda h: True) if scope is None else (lambda h: h in scope),
        lambda h: h in mentions,
        default)


class Order(unittest.TestCase):
    def test_a_mention_wins_from_a_follow_up(self):
        """Odin spoke last, but the human names the architect. Answering with
        odin because it happened to speak last is the bug this pins."""
        targets, reason = pick("@architect wat vind jij?",
                               earlier=[msg("pub-odin")],
                               mentions={"architect"})
        self.assertEqual((targets, reason), (["architect"], "mention"))

    def test_a_mention_wins_from_a_default(self):
        targets, reason = pick("@architect kijk hier eens naar",
                               default="odin", mentions={"architect"})
        self.assertEqual((targets, reason), (["architect"], "mention"))

    def test_a_follow_up_wins_from_a_default(self):
        """Odin is the default here AND spoke last; the reason must still say
        which rule fired, or the logs cannot tell a live conversation from a
        cold start."""
        targets, reason = pick("en verder?", earlier=[msg("pub-odin")],
                               default="odin")
        self.assertEqual((targets, reason), (["odin"], "vervolg"))

    def test_the_default_fires_only_on_a_cold_start(self):
        targets, reason = pick("ik zit te denken over X", default="odin")
        self.assertEqual((targets, reason), (["odin"], "default"))

    def test_without_a_default_a_cold_start_stays_silent(self):
        self.assertEqual(pick("ik zit te denken over X"), ([], ""))


class Scope(unittest.TestCase):
    def test_a_mention_of_an_agent_that_may_not_speak_here_is_ignored(self):
        targets, reason = pick("@architect hier dan?", mentions={"architect"},
                               scope={"odin"})
        self.assertEqual((targets, reason), ([], ""))

    def test_a_follow_up_only_in_the_agents_own_channel(self):
        """The architect spoke in #general as a relay member; that widens the
        mention branch, not the follow-up branch."""
        targets, reason = pick("en verder?", earlier=[msg("pub-architect")])
        self.assertEqual((targets, reason), ([], ""))

    def test_a_default_that_may_not_speak_is_a_startup_error_not_a_runtime_skip(self):
        """`pick` trusts the default because bootstrap.check_channel_defaults
        refuses to start with a bad one. Pinned here so removing that check
        cannot quietly turn into a silent skip."""
        import bootstrap
        with self.assertRaises(ValueError):
            bootstrap.check_channel_defaults({"general": "architect"}, AGENTS)
        with self.assertRaises(ValueError):
            bootstrap.check_channel_defaults({"general": "niemand"}, AGENTS)


class WindowAndHumans(unittest.TestCase):
    def test_only_the_most_recent_agent_counts(self):
        """Odin spoke, the architect spoke after it. Walking further back to
        find one that fits is how an agent wakes up on someone else's thread."""
        targets, reason = pick("en verder?",
                               earlier=[msg("pub-odin"), msg("pub-architect")])
        self.assertEqual((targets, reason), ([], ""))

    def test_a_recent_agent_that_may_not_speak_here_falls_through_to_the_default(self):
        """The architect answered in #general because it was @mentioned (relay
        membership widens mentions). A human then says something without a
        handle. The architect may not continue here, so this is a cold start
        for #general: the default answers. Silence would look exactly like a
        listener that is not running (design.md). Mark, 2026-09-23."""
        targets, reason = pick("en verder?", earlier=[msg("pub-architect")],
                               default="odin")
        self.assertEqual((targets, reason), (["odin"], "default"))

    def test_humans_in_between_do_not_break_a_follow_up(self):
        targets, reason = pick("en verder?",
                               earlier=[msg("pub-odin"), msg("pub-mark")])
        self.assertEqual((targets, reason), (["odin"], "vervolg"))

    def test_an_agent_outside_the_window_does_not_trigger(self):
        oud = [msg("pub-odin")] + [msg("pub-mark")] * triggers.FOLLOW_UP_WINDOW
        self.assertEqual(pick("en verder?", earlier=oud), ([], ""))
