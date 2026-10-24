# SPDX-License-Identifier: MIT
"""The boards follow the factory (Mark, 2026-10-24). The stage mapping is
pinned against the texts the listener actually writes; the gh side is
stubbed, and nothing moves unless the listener enabled the boards."""
import unittest

import board
import build_runner


class Stage(unittest.TestCase):
    def test_the_listener_texts_map_to_stages(self):
        cases = {
            "Build started by **odin** (image `9fec55d90895`). Run file: `x`.": "Building",
            "PR #217 opened from `habitat/builder/x`; it is merged once every check passes.": "CI",
            "PR #222 opened; merged once every check passes, then the change is built.": "CI",
            build_runner.comment("failed", "reviewer", {"why": "(dispatch exit 1)"}): "Blocked",
            "Not merged: failing: Fast test gate (offline).": "Blocked",
            "No PR: the session wrote nothing.": "Blocked",
            "Deployed to the homelab: wordsworth-api sha256:abc.": "Deployed",
            build_runner.comment("passed", "architect", {"branch": "b"}): None,
            "Merged PR #31 (2 checks passed).": "Merged",  # Done or Todo, by the issue's state
        }
        for text, stage in cases.items():
            self.assertEqual(board.stage_for(text), stage, text)

    def test_a_new_issue_starts_where_it_belongs(self):
        self.assertEqual(board.stage_for("b", title="propose: add-x"), "Writing change")
        self.assertEqual(board.stage_for("b", title="build: add-x"), "Todo")


class Note(unittest.TestCase):
    def tearDown(self):
        board.enable({})

    def test_only_repos_with_a_board_move(self):
        calls = []
        board.enable({"owner": "MWest2020", "boards": {"wordsworth": 1}})
        board.note("wordsworth", 9, "Build started by odin", popen=lambda a, **k: calls.append(a))
        board.note("ratatoskr", 9, "Build started by odin", popen=lambda a, **k: calls.append(a))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][-4:], ["wordsworth", "1", "9", "Building"])

    def test_off_until_enabled(self):
        calls = []
        board.note("wordsworth", 9, "Build started", popen=lambda a, **k: calls.append(a))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
