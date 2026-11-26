# SPDX-License-Identifier: MIT
"""A fixture cannot change without SHA256SUMS changing in the same commit.
See orchestrator/testdata/make_image_fixtures.py."""
import hashlib
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(HERE, "testdata")
SUMS = os.path.join(TESTDATA, "SHA256SUMS")
EXTS = (".png", ".jpg", ".webp")


class FixturesMatchTheirSums(unittest.TestCase):
    def test_every_sum_matches_and_every_image_is_listed(self):
        with open(SUMS) as f:
            rows = [ln.split(None, 1) for ln in f if ln.strip()]
        listed = {name.strip(): sha for sha, name in rows}
        on_disk = {n for n in os.listdir(TESTDATA) if n.endswith(EXTS)}
        self.assertEqual(on_disk, set(listed))
        for name, sha in listed.items():
            with open(os.path.join(TESTDATA, name), "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), sha,
                                  f"{name} does not match SHA256SUMS")


if __name__ == "__main__":
    unittest.main()
