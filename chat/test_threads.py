# SPDX-License-Identifier: MIT
"""Thread replies (reply-to-message): the parent is read from the relay's tags,
and a reply is sent as --reply-to with a validated id."""
import unittest

import actions
import threads
from test_actions import Base, Fake

PARENT = "9fb1c557ade26fdd9e4898f7eaf141d95f80400156a97ac3cce47c93e1e2c441"


class Parent(unittest.TestCase):
    def test_the_marked_reply_tag(self):
        # the exact shape the relay stored on 2026-10-23
        tags = [["h", "6a393454-8c03-46ee-a1d3-e11179ff8d89"], ["e", PARENT, "", "reply"]]
        self.assertEqual(threads.reply_parent(tags), PARENT)

    def test_positional_tags_and_none(self):
        self.assertEqual(threads.reply_parent([["e", "a" * 64], ["e", PARENT]]), PARENT)
        self.assertIsNone(threads.reply_parent([["h", "x"]]))
        self.assertIsNone(threads.reply_parent(None))
        self.assertIsNone(threads.reply_parent([["e", "a" * 64, "", "root"]]))


class Send(Base):
    def test_a_reply_is_sent_as_reply_to(self):
        fake = Fake()
        self.install(fake)
        self.assertEqual(actions.send("c1", "go ahead", reply_to=PARENT)[0], 200)
        args = fake.calls[0][1]
        self.assertEqual(args[args.index("--reply-to") + 1], PARENT)

    def test_a_plain_message_has_no_reply_to(self):
        fake = Fake()
        self.install(fake)
        actions.send("c1", "hello")
        self.assertNotIn("--reply-to", fake.calls[0][1])

    def test_a_malformed_parent_is_refused_and_nothing_is_sent(self):
        fake = Fake()
        self.install(fake)
        for bad in ("abc", "x" * 64, PARENT + " --channel evil", PARENT.upper()):
            code, body = actions.send("c1", "hi", reply_to=bad)
            self.assertEqual(code, 400, bad)
            self.assertIn("reply_to", body["error"])
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
