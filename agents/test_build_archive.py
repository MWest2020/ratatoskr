# SPDX-License-Identifier: MIT
"""After a merge (no deploy recipe) or a deploy, the change is archived; a
proposal or an archive itself never is (split from test_build_merge.py)."""
import tempfile
import unittest

import build_runner
import build_wiring


class ArchiveHooks(unittest.TestCase):
    def run_merge(self, recipe, kind=None):
        done = []

        class Merger:
            def checks(self, *a):
                return "merge", "2 checks passed"

            def merge(self, *a):
                return ""

            def merged_sha(self, *a):
                return "a" * 40, ""

        class Deployer:
            def recipe(self, repo):
                return {"x": 1} if recipe else None

            def step(self, d):
                return "wait", ""

        class Issues:
            def comment(self, *a):
                return ""
        with tempfile.TemporaryDirectory() as t:
            builds = build_runner.Builds({"owner": "MWest2020", "runs": t}, popen=None)
            builds.merging.append({"repo": "r", "change": "c", "issue": 9, "cid": "c", "pr": 31,
                                   "cname": "convergence",
                                   "next": 0, **({"kind": kind} if kind else {})})
            _, tick = build_wiring.setup({"owner": "MWest2020", "runs": t}, {}, "odin", "mark",
                                         lambda *a: True, issues=Issues(), builds=builds,
                                         merger=Merger(), deployer=Deployer(),
                                         after_done=done.append, log=lambda *a, **k: None)
            builds.tick = lambda on_event: None
            tick()
            return done, builds

    def test_no_recipe_archives_right_after_the_merge(self):
        done, _ = self.run_merge(recipe=False)
        self.assertEqual([d["change"] for d in done], ["c"])

    def test_with_a_recipe_it_waits_for_the_deploy(self):
        done, builds = self.run_merge(recipe=True)
        self.assertEqual(done, [])
        self.assertEqual(builds.deploying[0]["change"], "c")

    def test_the_deploy_keeps_the_channel_the_hub_is_woken_in(self):
        _, builds = self.run_merge(recipe=True)
        self.assertEqual(builds.deploying[0]["cname"], "convergence")

    def test_an_archive_merge_is_not_archived_again(self):
        done, _ = self.run_merge(recipe=False, kind="archive")
        self.assertEqual(done, [])


class ArchiveAfterDeploy(unittest.TestCase):
    def test_a_finished_deploy_archives_the_change(self):
        done = []

        class Deployer:
            def recipe(self, repo):
                return {"x": 1}

            def step(self, d):
                return "done", "wordsworth-api runs sha256:abc"

        class Issues:
            def comment(self, *a):
                return ""
        with tempfile.TemporaryDirectory() as t:
            builds = build_runner.Builds({"owner": "MWest2020", "runs": t}, popen=None)
            builds.deploying.append({"repo": "wordsworth", "issue": 9, "cid": "c",
                                     "change": "add-x", "phase": "verify", "started": 0})
            _, tick = build_wiring.setup({"owner": "MWest2020", "runs": t}, {}, "odin", "mark",
                                         lambda *a: True, issues=Issues(), builds=builds,
                                         deployer=Deployer(), after_done=done.append,
                                         log=lambda *a, **k: None)
            builds.tick = lambda on_event: None
            tick()
        self.assertEqual([d["change"] for d in done], ["add-x"])
        self.assertEqual(builds.deploying, [])


if __name__ == "__main__":
    unittest.main()
