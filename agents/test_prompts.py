# SPDX-License-Identifier: EUPL-1.2
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
