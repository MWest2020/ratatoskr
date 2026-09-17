# SPDX-License-Identifier: MIT
"""Offline tests for `bootstrap.py` (hub resolution by ROLE, not by name).
Run from agents/: `python3 -m unittest test_bootstrap` (agents/ has no
__init__.py and the modules use top-level imports, so the package path does not
work).
"""
import unittest

import bootstrap
import prompts


class HubAndRoleTest(unittest.TestCase):
    """The hub is found by ROLE. Three places in the listener used the name
    `coordinator`; after the rename to odin they silently fell back — the reader
    onto an agent with half the channel visibility, and the hub stopped getting
    its roster and liveness context."""

    def _root(self, body):
        import tempfile, pathlib
        d = tempfile.mkdtemp()
        pathlib.Path(d, "identities.yml").write_text(body)
        return d

    REG = ("identities:\n"
           "  mark:\n    rol: mens\n    status: actief\n    pubkey_hex: aa\n"
           "  coordinator:\n    rol: meta-agent\n    status: ingetrokken\n    pubkey_hex: bb\n"
           "  odin:\n    rol: meta-agent\n    status: actief\n    pubkey_hex: cc\n"
           "  bouwer:\n    rol: chat-agent\n    status: actief\n    pubkey_hex: dd\n")

    def test_hub_is_the_active_meta_agent(self):
        self.assertEqual(bootstrap.hub_handle(self._root(self.REG)), "odin")

    def test_revoked_hub_is_not_chosen(self):
        reg = self.REG.replace("  odin:\n    rol: meta-agent\n    status: actief\n    pubkey_hex: cc\n", "")
        self.assertIsNone(bootstrap.hub_handle(self._root(reg)))

    def test_roster_leaves_out_the_hub_itself(self):
        agents = {"odin": {"system": "hub", "channels": ["general"]},
                  "bouwer": {"system": "bouwt", "channels": ["bouw"]}}
        t = prompts.roster_text(agents, "odin")
        self.assertIn("@bouwer", t)
        self.assertNotIn("@odin", t)


if __name__ == "__main__":
    unittest.main()
