# SPDX-License-Identifier: MIT
"""Phase 3: a merge ends on the homelab. The push step runs against a real git
remote in a temp dir; GitHub's package API and kubectl are faked. alma is
refused by construction."""
import json
import os
import subprocess
import tempfile
import unittest

import deploy

OLD = "sha256:" + "a" * 64
NEW = "sha256:" + "b" * 64
IMG = "ghcr.io/mwest2020/wordsworth"
API = f"spec:\n  containers:\n  - image: {IMG}@{OLD}\n  - image: quay.io/oauth2-proxy/oauth2-proxy:v7\n"
INIT = f"image: {IMG}@{OLD}\n"


# Inside the pre-push hook git exports GIT_DIR and friends; a git call here
# would then act on the OUTER repository (the lesson of test_work_tree, 0b84e2d).
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(*a, cwd=None):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True,
                   env=CLEAN)


class Pure(unittest.TestCase):
    def test_bump_touches_only_the_image(self):
        new, n = deploy.bump(API, IMG, NEW)
        self.assertEqual(n, 1)
        self.assertIn(f"{IMG}@{NEW}", new)
        self.assertIn("oauth2-proxy:v7", new)

    def test_alma_and_strays_are_refused(self):
        self.assertTrue(deploy.safe_paths(["cluster-config/infra/wordsworth/api.yaml"]))
        for bad in (["cluster-config/infra/alma/api.yaml"], ["prod/alma.yaml"],
                    ["cluster-config/infra/../alma/x.yaml"], ["cluster-config/x.yaml"]):
            self.assertFalse(deploy.safe_paths(bad), bad)


class Steps(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = self.t.name
        remote, seed = os.path.join(t, "remote.git"), os.path.join(t, "seed")
        git("init", "-q", "--bare", "-b", "main", remote)
        git("clone", "-q", remote, seed)
        d = os.path.join(seed, "cluster-config/infra/wordsworth")
        os.makedirs(d)
        open(os.path.join(d, "api.yaml"), "w").write(API)
        open(os.path.join(d, "init-job.yaml"), "w").write(INIT)
        git("add", ".", cwd=seed)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seed", cwd=seed)
        git("push", "-q", "origin", "HEAD:main", cwd=seed)
        self.remote, self.seed = remote, seed
        self.kube = []
        self.cfg = {"owner": "MWest2020",
                    "homelab": {"repo_dir": seed, "worktree": os.path.join(t, "wt"),
                                "kubectl": "kubectl"},
                    "deploy": {"wordsworth": {
                        "package": "wordsworth", "image": IMG, "app": "wordsworth",
                        "namespace": "wordsworth", "deployment": "wordsworth-api",
                        "manifests": ["cluster-config/infra/wordsworth/api.yaml",
                                      "cluster-config/infra/wordsworth/init-job.yaml"]}}}
        self.clock = [1000.0]
        self.dep_image = IMG + "@" + OLD

        def runner(argv, **kw):
            if argv[0] == "gh":
                rows = [{"name": NEW, "metadata": {"container": {"tags": ["sha-1234567"]}}}]
                return subprocess.CompletedProcess(argv, 0, json.dumps(rows), "")
            if argv[0] == "kubectl":
                self.kube.append(argv)
                if "get" in argv:
                    dep = {"metadata": {"generation": 2}, "spec": {"replicas": 1, "template": {
                        "spec": {"containers": [{"image": self.dep_image}]}}},
                        "status": {"observedGeneration": 2, "updatedReplicas": 1,
                                   "availableReplicas": 1}}
                    return subprocess.CompletedProcess(argv, 0, json.dumps(dep), "")
                return subprocess.CompletedProcess(argv, 0, "", "")
            return subprocess.run(argv, env=CLEAN, **kw)
        self.d = deploy.Deployer(self.cfg, runner=runner, now=lambda: self.clock[0])
        self.job = {"repo": "wordsworth", "issue": 9, "sha": "1234567" + "0" * 33,
                    "phase": "image", "started": 1000.0}

    def tearDown(self):
        self.t.cleanup()

    def test_the_whole_road(self):
        self.assertEqual(self.d.step(self.job)[0], "next")          # image found
        self.assertEqual(self.job["digest"], NEW)
        state, msg = self.d.step(self.job)                          # push
        self.assertEqual(state, "next", msg)
        check = os.path.join(self.t.name, "check")
        git("clone", "-q", self.remote, check)
        for f in ("api.yaml", "init-job.yaml"):
            body = open(os.path.join(check, "cluster-config/infra/wordsworth", f)).read()
            self.assertIn(f"{IMG}@{NEW}", body, f)
        self.assertEqual(self.d.step(self.job)[0], "next")          # sync
        self.assertIn("argocd.argoproj.io/refresh=hard", self.kube[-1])
        self.assertEqual(self.d.step(self.job)[0], "wait")          # still old image
        self.dep_image = IMG + "@" + NEW
        self.assertEqual(self.d.step(self.job)[0], "done")

    def test_a_missing_image_waits_then_fails(self):
        self.job["sha"] = "7654321" + "0" * 33
        self.assertEqual(self.d.step(self.job), ("wait", ""))
        self.clock[0] += deploy.IMAGE_WAIT_S + 1
        self.assertEqual(self.d.step(self.job)[0], "fail")

    def test_no_recipe_no_deploy(self):
        self.job["repo"] = "alma"
        self.assertEqual(self.d.step(self.job)[0], "fail")
        self.cfg["deploy"]["wordsworth"]["manifests"] = ["cluster-config/infra/alma/x.yaml"]
        self.assertIsNone(self.d.recipe("wordsworth"))

    def test_a_manifest_without_the_image_stops_the_deploy(self):
        # Bumping only api.yaml would leave init-job on the old digest: the
        # migrations the new api needs would never run.
        f = os.path.join(self.seed, "cluster-config/infra/wordsworth/init-job.yaml")
        open(f, "w").write("image: someone/else:1\n")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "drift", cwd=self.seed)
        git("push", "-q", "origin", "HEAD:main", cwd=self.seed)
        self.d.step(self.job)
        state, msg = self.d.step(self.job)
        self.assertEqual(state, "fail")
        self.assertIn("init-job.yaml", msg)
        wt = self.cfg["homelab"]["worktree"]
        dirty = subprocess.run(["git", "-C", wt, "status", "--porcelain"], capture_output=True,
                               text=True, env=CLEAN).stdout
        self.assertEqual(dirty, "", "a failed bump must leave the worktree clean")


if __name__ == "__main__":
    unittest.main()
