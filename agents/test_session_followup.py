# SPDX-License-Identifier: MIT
"""A finished session the hub started wakes the hub (2026-10-23: odin planned to
consult "when the report arrives", and the report never woke it)."""
import unittest

import session_followup as sf


class Reg:
    def __init__(self, finished):
        self.finished = list(finished)


class Wake(unittest.TestCase):
    def test_the_hubs_session_gets_one_follow_up_turn(self):
        turns = []
        reg = Reg([{"type": "wordsworth", "starter": "odin", "requester": "orchestrator",
                    "cid": "c", "cname": "general"},
                   {"type": "research", "starter": "mark", "requester": "mark",
                    "cid": "c", "cname": "general"}])
        sf.wake_hub(reg, "odin", lambda cid: [{"content": "report"}],
                    lambda *a, **k: turns.append((a, k)), log=lambda *a, **k: None)
        self.assertEqual(len(turns), 1)                     # only the hub's session
        a, k = turns[0]
        self.assertEqual((a[0], a[1], a[8]), ("odin", "general", "session-done"))
        self.assertEqual(a[6], "orchestrator")              # the requester keeps its rights
        self.assertTrue(k["followup"])
        self.assertIn("Do not start another session", a[5])
        self.assertEqual(reg.finished, [])

    def test_an_unreadable_channel_is_logged_not_guessed(self):
        logs = []
        reg = Reg([{"type": "x", "starter": "odin", "cid": "c", "cname": "general"}])
        sf.wake_hub(reg, "odin", lambda cid: None, lambda *a, **k: self.fail("no turn"),
                    log=lambda *a, **k: logs.append(a[0]))
        self.assertIn("hub not woken", logs[0])


if __name__ == "__main__":
    unittest.main()
