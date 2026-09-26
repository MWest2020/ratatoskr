"""De bronregel van _live.md: wanneer is een werkkopie afwijkend.

Tot 2026-09-26 las een uitgerolde boom die precies op origin/main stond als
"niet op main (HEAD)", alleen omdat hij detached was. De eigenschap is niet de
naam van de branch, maar of de boom iets heeft wat main niet heeft, of iets mist.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live import tree_warnings  # noqa: E402


class TreeWarnings(unittest.TestCase):
    def test_detached_exactly_on_main_is_not_deviating(self):
        self.assertEqual(tree_warnings("0", "0", 0), [])

    def test_behind_main_is_deviating(self):
        self.assertEqual(tree_warnings("0", "16", 0), ["16 commits achter origin/main"])

    def test_commits_not_on_main_are_deviating(self):
        self.assertEqual(tree_warnings("2", "0", 0),
                         ["2 commits die niet op origin/main staan"])

    def test_local_edits_are_deviating(self):
        self.assertEqual(tree_warnings("0", "0", 3), ["3 ongecommitte wijziging(en)"])

    def test_unknown_counts_do_not_raise_a_false_alarm(self):
        self.assertEqual(tree_warnings("?", "?", 0), [])


if __name__ == "__main__":
    unittest.main()
