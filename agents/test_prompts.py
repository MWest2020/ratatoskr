# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor `prompts.py` (mention-match + kanaalkennis-bestanden).
Draaien vanuit agents/: `python3 -m unittest test_prompts` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
"""
import unittest

import prompts


class Mentioned(unittest.TestCase):
    def test_word_boundary(self):
        self.assertTrue(prompts.mentioned("hoi @architect kijk", "architect"))
        self.assertTrue(prompts.mentioned("@architect.", "architect"))
        self.assertFalse(prompts.mentioned("kijk in @architectuur", "architect"))
        self.assertFalse(prompts.mentioned("geen mention", "architect"))
        self.assertFalse(prompts.mentioned("deploy@bouwer.example", "bouwer"))  # linker grens
        self.assertTrue(prompts.mentioned("HOI @Coordinator", "coordinator"))  # case-insens


class ChannelKnowledge(unittest.TestCase):
    def test_path_traversal_refused(self):
        # onveilige (relay-geleverde) kanaalnaam mag geen bestand buiten knowledge/ lezen
        for bad in ["../../etc/passwd", "..", "a/b", "x/../y", "/etc/hosts", ""]:
            self.assertEqual(prompts.channel_knowledge("/tmp", bad), "")


if __name__ == "__main__":
    unittest.main()
