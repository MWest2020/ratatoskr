# SPDX-License-Identifier: MIT
"""The identity registry as the chat backend reads it.

`identities.yml` is read here with regexes (stdlib, no yaml dependency on the
VM). That works, but it means the shape of that file is a contract. These tests
pin that contract, including the two properties something really depended on
today: revoked keys do not count, and the hub is found by ROLE so a rename breaks
nothing.
"""
import unittest

import roster

REG = """# commentaar
identities:
  mark:
    rol: mens
    status: actief
    pubkey_hex: aa11
    npub: npub1mark
  coordinator:
    rol: meta-agent
    status: ingetrokken
    pubkey_hex: bb22
  odin:
    rol: meta-agent
    status: actief
    pubkey_hex: cc33
  bouwer:
    rol: chat-agent
    status: actief
    pubkey_hex: dd44
  security:
    rol: chat-agent
    status: actief
    pubkey_hex: null
  odin-worker:
    rol: sessie
    status: actief
    pubkey_hex: ee55
"""


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.m = roster._parse_identities(REG)

    def test_active_identities_with_a_key(self):
        self.assertEqual(sorted(v["name"] for v in self.m.values()),
                         ["bouwer", "mark", "odin", "odin-worker"])

    def test_revoked_is_dropped(self):
        self.assertNotIn("bb22", self.m)          # the old coordinator key

    def test_without_a_pubkey_is_dropped(self):
        self.assertFalse(any(v["name"] == "security" for v in self.m.values()))

    def test_the_role_is_carried_along(self):
        self.assertEqual(self.m["cc33"], {"name": "odin", "rol": "meta-agent"})

    def test_a_name_with_a_hyphen(self):
        # odin-worker used to be versum; the rename introduced a hyphen in a
        # handle and the block regex has to cope with that.
        self.assertEqual(self.m["ee55"]["name"], "odin-worker")

    def test_a_quoted_status_counts_too(self):
        m = roster._parse_identities(REG.replace("status: actief", "status: 'actief'"))
        self.assertIn("cc33", m)

    def test_an_empty_file_gives_an_empty_map(self):
        self.assertEqual(roster._parse_identities(""), {})


class HubTest(unittest.TestCase):
    """hub_pubkey() finds the hub by role. Looking it up by name broke three times
    today: `coordinator` no longer existed and everything silently fell back."""

    def _with(self, reg):
        roster._cache.update(t=9e18, data=roster._parse_identities(reg), ttl=9e18)

    def tearDown(self):
        roster._cache.update(t=0, data=None, ttl=0)

    def test_the_hub_is_the_active_meta_agent(self):
        self._with(REG)
        self.assertEqual(roster.name_of(roster.hub_pubkey()), "odin")

    def test_a_revoked_meta_agent_is_not_chosen(self):
        self._with(REG.replace("  odin:\n    rol: meta-agent\n    status: actief\n    pubkey_hex: cc33\n", ""))
        self.assertIsNone(roster.hub_pubkey())

    def test_renaming_does_not_break_the_lookup(self):
        self._with(REG.replace("  odin:", "  wodan:"))
        self.assertEqual(roster.name_of(roster.hub_pubkey()), "wodan")

    def test_agent_pubkey_only_for_agents(self):
        self._with(REG)
        self.assertIsNotNone(roster.agent_pubkey("odin"))       # meta-agent
        self.assertIsNotNone(roster.agent_pubkey("bouwer"))     # chat-agent
        self.assertIsNone(roster.agent_pubkey("mark"))          # the human
        self.assertIsNone(roster.agent_pubkey("odin-worker"))   # a session
        self.assertIsNone(roster.agent_pubkey("coordinator"))   # revoked

    def test_agent_pubkey_is_case_insensitive(self):
        self._with(REG)
        self.assertEqual(roster.agent_pubkey("ODIN"), roster.agent_pubkey("odin"))


if __name__ == "__main__":
    unittest.main()
