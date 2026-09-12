# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor `bootstrap.py` (hub-resolutie op ROL, niet op naam).
Draaien vanuit agents/: `python3 -m unittest test_bootstrap` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
"""
import unittest

import bootstrap
import prompts


class HubAndRoleTest(unittest.TestCase):
    """De hub wordt op ROL gevonden. Drie plekken in de listener stonden op de
    naam `coordinator`; na de hernoeming naar odin vielen die stil terug — de
    reader op een agent met halve kanaal-zichtbaarheid, en de hub kreeg zijn
    roster- en liveness-context niet meer."""

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
