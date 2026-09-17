# SPDX-License-Identifier: MIT
"""De koppeling marker → sessie, zonder relay en zonder agents.

Deze code zat in listener.py en werd alleen indirect geraakt. Bij het uithalen
hoort hij een eigen suite te krijgen: een weigering die stil blijft ziet eruit
als een sessie die niets vond, en dat is precies de fout die je niet ziet.
"""
import unittest

import session_wiring

AGENTS = {"odin": {"nsec": "n-odin", "npub": "p-odin"},
          "bouwer": {"nsec": "n-bouwer", "npub": "p-bouwer"}}


class Reg:
    def __init__(self, sessie=None, reden=""):
        self.sessie, self.reden, self.calls = sessie, reden, []

    def start(self, *a):
        self.calls.append(a)
        return self.sessie, self.reden


def sessie(identity="odin", cid="cid-1", max_s=1800):
    return {"identity": identity, "cid": cid, "max_s": max_s}


class Starting(unittest.TestCase):
    def setUp(self):
        self.posts = []
        self.logs = []

    def wire(self, reg):
        return session_wiring.build(
            reg, AGENTS, lambda cid, t, nsec, npub: self.posts.append((cid, t, nsec)),
            "odin", log=lambda *a, **k: self.logs.append(a[0]))

    def test_no_marker_starts_nothing(self):
        reg = Reg()
        _, try_session = self.wire(reg)
        try_session("gewoon een bericht", "mark", "mark", "general", "cid-1")
        self.assertEqual(reg.calls, [])
        self.assertEqual(self.posts, [])

    def test_a_started_session_announces_itself(self):
        reg = Reg(sessie())
        _, try_session = self.wire(reg)
        try_session("!sessie ratatoskr kijk eens", "mark", "mark", "general", "cid-1")
        self.assertEqual(len(reg.calls), 1)
        self.assertIn("session `ratatoskr` started by @mark", self.posts[0][1])
        self.assertIn("30 min", self.posts[0][1])
        # Onder de identiteit die het TYPE opgeeft, niet die van de vrager.
        self.assertEqual(self.posts[0][2], "n-odin")

    def test_on_behalf_is_visible(self):
        reg = Reg(sessie())
        _, try_session = self.wire(reg)
        try_session("!sessie ratatoskr iets", "odin", "mark", "general", "cid-1")
        self.assertIn("on behalf of @mark", self.posts[0][1])

    def test_a_refusal_is_said_out_loud(self):
        reg = Reg(None, "limiet bereikt")
        _, try_session = self.wire(reg)
        try_session("!sessie ratatoskr iets", "mark", "mark", "general", "cid-1")
        self.assertEqual(len(self.posts), 1)
        self.assertIn("no session: limiet bereikt", self.posts[0][1])
        self.assertEqual(self.posts[0][0], "cid-1", "de weigering hoort in HET kanaal")

    def test_progress_uses_the_type_identity(self):
        post, _ = self.wire(Reg())
        post(sessie(identity="bouwer", cid="cid-bouw"), "⋯ bezig")
        self.assertEqual(self.posts, [("cid-bouw", "⋯ bezig", "n-bouwer")])

    def test_an_unknown_identity_posts_nothing_instead_of_crashing(self):
        post, _ = self.wire(Reg())
        post(sessie(identity="bestaat-niet"), "⋯ bezig")
        self.assertEqual(self.posts, [])


if __name__ == "__main__":
    unittest.main()
