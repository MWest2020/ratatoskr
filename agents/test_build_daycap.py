# SPDX-License-Identifier: MIT
"""The day cap counts chains that reached the builder; the breaker counts all."""
import json
import os
import tempfile
import time
import unittest

import build


def run_file(d, name, change, roles, started):
    with open(os.path.join(d, name), "w") as fh:
        fh.write(json.dumps({"repo": "wordsworth", "change": change, "started": started}) + "\n")
        for r in roles:
            fh.write(f"[dispatch] Job=habitat-{r}-x rol={r} change={change}\n")


class DayCap(unittest.TestCase):
    def test_an_architect_fail_does_not_spend_a_slot(self):
        now = time.time()
        with tempfile.TemporaryDirectory() as d:
            run_file(d, "wordsworth-a-1.log", "a", ["architect"], now)
            run_file(d, "wordsworth-b-1.log", "b", ["architect", "builder", "reviewer"], now)
            self.assertEqual(build.builds_today(d, lambda: now), 1)

    def test_the_breaker_counts_every_attempt_of_a_change(self):
        now = time.time()
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                run_file(d, f"wordsworth-a-{i}.log", "a", ["architect"], now)
            self.assertEqual(build.change_builds_today(d, "wordsworth", "a", lambda: now), 3)


if __name__ == "__main__":
    unittest.main()
