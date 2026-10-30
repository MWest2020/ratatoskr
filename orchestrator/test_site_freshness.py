# SPDX-License-Identifier: MIT
"""The weekly site-freshness checks (site_checks) and their digest entry."""
import datetime
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_checks  # noqa: E402
import status_digest  # noqa: E402

RENAMES = """
renames:
  - old: Boomhuis
    new: Ratatoskr
parked: [crible]
"""


class Renames(unittest.TestCase):
    def test_the_shared_file_is_read(self):
        renames, parked = site_checks.load_renames(RENAMES)
        self.assertEqual(renames, [("Boomhuis", "Ratatoskr")])
        self.assertEqual(parked, ["crible"])

    def test_an_old_name_is_found_and_a_formerly_mention_is_not(self):
        pages = {"p.md": "## Boomhuis\n\nRatatoskr (eerder \"Boomhuis\") is the layer.\nex-boomhuis"}
        found = site_checks.stale_names(pages, [("Boomhuis", "Ratatoskr")])
        self.assertEqual([(f["line"], f["new"]) for f in found], [(1, "Ratatoskr")])

    def test_the_fix_keeps_the_case_and_the_history(self):
        text = "## Boomhuis\nboomhuis runs. Ratatoskr (formerly \"Boomhuis\")."
        found = site_checks.stale_names({"p": text}, [("Boomhuis", "Ratatoskr")])
        fixed = site_checks.apply_mechanical(text, found)
        self.assertEqual(fixed, "## Ratatoskr\nratatoskr runs. Ratatoskr (formerly \"Boomhuis\").")


class Visibility(unittest.TestCase):
    def test_a_private_claim_about_a_public_repo(self):
        pages = {"p.md": "## X\nThe repo is private, but see "
                         "[code](https://github.com/MWest2020/ratatoskr)."}
        found = site_checks.visibility(pages, lambda r: "PUBLIC")
        self.assertEqual(found[0]["check"], "visibility")
        self.assertEqual(found[0]["kind"], "narrative")

    def test_a_true_claim_is_left_alone(self):
        pages = {"p.md": "## X\nThe repo is private: github.com/MWest2020/convergence"}
        self.assertEqual(site_checks.visibility(pages, lambda r: "PRIVATE"), [])


class Projects(unittest.TestCase):
    def test_missing_and_parked(self):
        pages = {"p.md": "[a](https://github.com/MWest2020/wordsworth) "
                         "[b](https://github.com/MWest2020/crible)"}
        found = site_checks.projects(pages, ["wordsworth", "homelab"], {"crible"}, set())
        self.assertEqual(sorted(f["check"] for f in found), ["missing-project", "parked-project"])
        self.assertIn("homelab", found[0]["message"])


class Links(unittest.TestCase):
    def test_moved_is_mechanical_and_gone_is_narrative(self):
        pages = {"p.md": "github.com/MWest2020/old-name and github.com/MWest2020/gone"}
        found = site_checks.links(pages, lambda r: {"old-name": "new-name"}.get(r))
        kinds = {f["check"]: f["kind"] for f in found}
        self.assertEqual(kinds, {"moved-link": "mechanical", "broken-link": "narrative"})
        fixed = site_checks.apply_mechanical(pages["p.md"], found)
        self.assertIn("MWest2020/new-name", fixed)


class Descriptions(unittest.TestCase):
    def test_a_section_far_from_the_goal_is_flagged(self):
        body = ("## Wordsworth — x\n\nTomatoes cabbages and carrots grow nicely here.\n\n"
                "[code](https://github.com/MWest2020/wordsworth)")
        goals = {"wordsworth": "A sovereign pipeline that pseudonymises government documents"}
        self.assertEqual(len(site_checks.descriptions({"p": body}, goals)), 1)

    def test_a_close_section_is_not(self):
        body = ("## Wordsworth — x\n\nA sovereign pipeline that pseudonymises government "
                "documents.\n\n[code](https://github.com/MWest2020/wordsworth)")
        goals = {"wordsworth": "A sovereign pipeline that pseudonymises government documents"}
        self.assertEqual(site_checks.descriptions({"p": body}, goals), [])


class Digest(unittest.TestCase):
    NOW = datetime.datetime(2026, 10, 30, 12, tzinfo=datetime.timezone.utc)

    def test_recent_findings_become_one_impediment(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "s.json")
            json.dump({"generated": "2026-10-30T06:00:00+00:00", "pr": "https://x/pr/1",
                       "findings": [{"message": "a"}, {"message": "b"}, {"message": "c"}]},
                      open(path, "w"))
            [imp] = status_digest.site_stale(self.NOW, path)
            self.assertEqual(imp["kind"], "site-stale")
            self.assertIn("3 finding(s)", imp["why"])

    def test_old_or_empty_runs_say_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "s.json")
            json.dump({"generated": "2026-10-01T06:00:00+00:00", "findings": [{"message": "a"}]},
                      open(path, "w"))
            self.assertEqual(status_digest.site_stale(self.NOW, path), [])
            self.assertEqual(status_digest.site_stale(self.NOW, os.path.join(t, "none")), [])


if __name__ == "__main__":
    unittest.main()
