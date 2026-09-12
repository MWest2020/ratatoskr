# SPDX-License-Identifier: EUPL-1.2
"""What the read routes answer once a request is past the gate (read_routes.py).

The invariant these tests guard: a raw upstream error never comes back on a user
input error, and an empty board is distinguishable from a broken producer.
"""
import json
import unittest

from live_server import CID, LiveServerCase, read_routes


class ReadRoutesTest(LiveServerCase):
    PERSON = "reader"

    # --- work overview ---
    def test_board_without_a_snapshot_is_404_with_an_explanation(self):
        """An empty board must be distinguishable from a broken producer."""
        old = read_routes.board.PATH
        read_routes.board.PATH = "/bestaat/niet/board.json"
        try:
            code, body = self.call("/api/board")
        finally:
            read_routes.board.PATH = old
        self.assertEqual(code, 404)
        self.assertIn("hint", body)

    # --- messages, PRs and pinned context ---
    def test_messages_come_sorted_by_time(self):
        _, body = self.call(f"/api/messages?channel={CID}")
        ts = [m["ts"] for m in json.loads(body)["messages"]]
        self.assertEqual(ts, sorted(ts))

    def test_unknown_channel_is_400_not_502(self):
        self.assertEqual(self.call("/api/messages?channel=nope")[0], 400)

    def test_the_repo_parameter_is_validated(self):
        self.assertEqual(self.call("/api/prs?repo=MWest2020/x")[0], 200)
        for bad in ("", "zonder-owner", "../etc", "a/b/c"):
            self.assertEqual(self.call("/api/prs?repo=" + bad)[0], 400, bad)
        self.assertEqual(self.call("/api/pr?repo=MWest2020/x&num=abc")[0], 400)

    def test_pinned_with_an_odd_channel_gives_empty_not_broken(self):
        code, body = self.call("/api/pinned?channel=../../etc")
        self.assertEqual((code, json.loads(body)), (200, {"content": ""}))


if __name__ == "__main__":
    unittest.main()
