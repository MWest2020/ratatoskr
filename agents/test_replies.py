# SPDX-License-Identifier: MIT
"""A reply addresses the agent it replies to (reply-to-message): the parent from
the relay's tags, the order against @mention and follow-up, and the room's issue."""
import unittest

import replies
import triggers
from test_room_flow import Room

PID = "9fb1c557ade26fdd9e4898f7eaf141d95f80400156a97ac3cce47c93e1e2c441"
AGENTS = {"architect": {"channels": ["architectuur"]}, "bouwer": {"channels": ["bouw"]}}
P2N = {"pa": "architect", "pb": "bouwer", "pm": "mark"}


def reply(to, content="go ahead"):
    return {"pubkey": "pm", "content": content, "tags": [["h", "c"], ["e", to, "", "reply"]]}


class Parent(unittest.TestCase):
    def test_the_relays_shape_and_the_old_one(self):
        self.assertEqual(replies.parent_id(reply(PID)), PID)
        self.assertEqual(replies.parent_id({"tags": [["e", "a" * 64], ["e", PID]]}), PID)
        self.assertIsNone(replies.parent_id({"tags": [["h", "c"]]}))

    def test_only_a_parent_in_this_channel_counts(self):
        msgs = [{"id": PID, "pubkey": "pb", "content": "plan"}]
        self.assertEqual(replies.parent_of(reply(PID), msgs)["pubkey"], "pb")
        self.assertIsNone(replies.parent_of(reply("b" * 64), msgs))
        self.assertEqual(replies.agent_of(msgs[0], P2N, AGENTS), "bouwer")
        self.assertIsNone(replies.agent_of({"pubkey": "pm"}, P2N, AGENTS))


class Pick(unittest.TestCase):
    def pick(self, content, replied, may=lambda h: True, earlier=()):
        return triggers.pick(content, list(earlier), "bouw", AGENTS, P2N, may,
                             lambda h: f"@{h}" in content, None, replied=replied)

    def test_a_reply_without_at_addresses_the_agent(self):
        self.assertEqual(self.pick("go ahead", "bouwer"), (["bouwer"], "reply"))

    def test_an_explicit_mention_wins(self):
        self.assertEqual(self.pick("@architect what do you think", "bouwer"),
                         (["architect"], "mention"))

    def test_scope_still_holds(self):
        self.assertEqual(self.pick("go ahead", "bouwer", may=lambda h: False), ([], ""))

    def test_no_reply_falls_back_as_before(self):
        self.assertEqual(self.pick("hello", None), ([], ""))


class InTheRoom(unittest.TestCase):
    def test_a_reply_continues_the_parents_issue_and_addresses_its_agent(self):
        r = Room({})
        parent = {"id": PID, "pubkey": "pa", "content": "the plan\n\n· ratatoskr#57"}
        earlier = [parent, {"pubkey": "pb", "content": "other work\n\n· ratatoskr#58"}]
        msgs = earlier + [reply(PID)]
        r.handle("werkplaats", "cid", msgs, len(msgs) - 1, "go ahead", "mark", "m1",
                 lambda h: False, parent=parent)
        self.assertEqual(r.turns[0][0], "architect")
        self.assertEqual(r.issues.calls[0][:3], ("comment", "ratatoskr", 57))


if __name__ == "__main__":
    unittest.main()
