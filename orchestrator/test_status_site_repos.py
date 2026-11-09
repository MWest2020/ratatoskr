# SPDX-License-Identifier: MIT
"""Which projects the overview at westerweel.work/nu/ covers (status_site.repos)."""
import datetime
import os
import tempfile
import time
import unittest

import status_site


class Repos(unittest.TestCase):
    def test_base_projects_include_bazibo(self):
        # Mark, 2026-11-07: the children's games app gets a roadmap on the overview;
        # its repo was renamed from bubbels to bazibo on 2026-11-09.
        now = datetime.datetime.now(datetime.timezone.utc)
        with tempfile.TemporaryDirectory() as runs:
            self.assertEqual(status_site.repos(now, runs), status_site.BASE)
        self.assertIn("bazibo", status_site.BASE)
        self.assertNotIn("bubbels", status_site.BASE)

    def test_a_repo_built_this_week_is_added_once(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        with tempfile.TemporaryDirectory() as runs:
            for name in ("netnl-a-1.log", "netnl-b-2.log", "bazibo-c-3.log"):
                open(os.path.join(runs, name), "w").close()
            old = os.path.join(runs, "crible-x-1.log")
            open(old, "w").close()
            stale = time.time() - 8 * 86400
            os.utime(old, (stale, stale))
            found = status_site.repos(now, runs)
        self.assertEqual(found, status_site.BASE + ["netnl"])


if __name__ == "__main__":
    unittest.main()
