# SPDX-License-Identifier: MIT
"""Offline tests for `prompts.py` (mention match + channel knowledge files).
Run from agents/: `python3 -m unittest test_prompts` (agents/ has no __init__.py
and the modules use top-level imports, so the package path does not work).
"""
import unittest

import prompts


class Mentioned(unittest.TestCase):
    def test_word_boundary(self):
        self.assertTrue(prompts.mentioned("hoi @architect kijk", "architect"))
        self.assertTrue(prompts.mentioned("@architect.", "architect"))
        self.assertFalse(prompts.mentioned("kijk in @architectuur", "architect"))
        self.assertFalse(prompts.mentioned("geen mention", "architect"))
        self.assertFalse(prompts.mentioned("deploy@bouwer.example", "bouwer"))  # left boundary
        self.assertTrue(prompts.mentioned("HOI @Coordinator", "coordinator"))  # case-insens


class ChannelKnowledge(unittest.TestCase):
    def test_path_traversal_refused(self):
        # an unsafe (relay-supplied) channel name must not read outside knowledge/
        for bad in ["../../etc/passwd", "..", "a/b", "x/../y", "/etc/hosts", ""]:
            self.assertEqual(prompts.channel_knowledge("/tmp", bad), "")


if __name__ == "__main__":
    unittest.main()


def test_route_clause_zwijgt_zonder_routes():
    # Geen rechten, geen zin. Anders leert een agent over een knop die hij niet
    # heeft en verspilt hij er beurten aan.
    assert prompts.route_clause({}) == ""
    assert prompts.route_clause({"routes": []}) == ""


def test_route_clause_noemt_alleen_de_toegestane_kanalen():
    t = prompts.route_clause({"routes": ["bouw", "review"]})
    assert "#bouw" in t and "#review" in t
    assert "!forward" in t and "message-id" in t


def test_ids_staan_alleen_in_de_prompt_als_er_doorgestuurd_mag_worden():
    # Zonder zichtbaar id kan een agent niets aanwijzen en is !forward
    # onbruikbaar; mét ids voor een agent die niets mag doorsturen is het ruis.
    recent = [{"id": "abcd1234efgh", "pubkey": "pk", "content": "hallo"}]
    namen = {"pk": "mark"}
    zonder = prompts.build_prompt("odin", "general", recent, "hallo", namen)
    met = prompts.build_prompt("odin", "general", recent, "hallo", namen, met_ids=True)
    assert "[abcd1234]" not in zonder
    assert "[abcd1234] mark: hallo" in met
