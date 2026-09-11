# SPDX-License-Identifier: EUPL-1.2
"""De serveerkant van het werk-overzicht: lezen, ouderdom, en de drie manieren
waarop het mis kan gaan. Een leeg bord moet te onderscheiden zijn van een kapotte
producent — dat onderscheid is het hele punt."""
import json
import os
import tempfile
import time
import unittest

import board


class Read(unittest.TestCase):
    def _file(self, data):
        pad = os.path.join(tempfile.mkdtemp(), "board.json")
        with open(pad, "w") as f:
            json.dump(data, f)
        return pad

    def test_missing_is_404_with_a_hint(self):
        payload, code = board.read("/bestaat/echt/niet.json")
        self.assertEqual(code, 404)
        self.assertIn("hint", payload)

    def test_broken_json_is_500_not_a_crash(self):
        pad = os.path.join(tempfile.mkdtemp(), "board.json")
        with open(pad, "w") as f:
            f.write("{ dit is geen json")
        payload, code = board.read(pad)
        self.assertEqual(code, 500)
        self.assertIn("unreadable", payload["error"])

    def test_fresh_snapshot(self):
        payload, code = board.read(self._file({"generated_at": time.time(), "cards": []}))
        self.assertEqual(code, 200)
        self.assertFalse(payload["stale_snapshot"])
        self.assertLess(payload["age_seconds"], 5)

    def test_old_snapshot_says_so(self):
        """Stil een oud bord tonen is precies de false-clear die we niet willen."""
        oud = time.time() - board.STALE_AFTER - 60
        payload, _ = board.read(self._file({"generated_at": oud, "cards": []}))
        self.assertTrue(payload["stale_snapshot"])

    def test_missing_timestamp_counts_as_stale(self):
        payload, _ = board.read(self._file({"cards": []}))
        self.assertTrue(payload["stale_snapshot"])


if __name__ == "__main__":
    unittest.main()
