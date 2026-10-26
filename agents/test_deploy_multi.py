# SPDX-License-Identifier: MIT
"""A recipe with several images (convergence: a server and a web image per
commit, pinned as `<image>:sha-<7>@sha256:<hex>`). Same fakes as test_deploy:
a real git remote in a temp dir, GitHub's package API and kubectl faked."""
import json
import os
import subprocess
import tempfile
import unittest

import deploy
from test_deploy import CLEAN, git

OLD = "sha256:" + "a" * 64
SRV_NEW, WEB_NEW = "sha256:" + "c" * 64, "sha256:" + "d" * 64
SRV, WEB = "ghcr.io/mwest2020/convergence-server", "ghcr.io/mwest2020/convergence-web"
MANIFEST = (f"containers:\n  - name: server\n    image: {SRV}:sha-0000000@{OLD}\n"
            f"  - name: web\n    image: {WEB}:sha-0000000@{OLD}\n"
            f"  - name: other\n    image: {SRV}-other:sha-0000000@{OLD}\n")


class Bump(unittest.TestCase):
    def test_tag_and_digest_are_rewritten_together(self):
        new, n = deploy.bump(MANIFEST, SRV, SRV_NEW, "sha-1234567")
        self.assertEqual(n, 1)
        self.assertIn(f"{SRV}:sha-1234567@{SRV_NEW}", new)
        self.assertIn(f"{WEB}:sha-0000000@{OLD}", new)          # another image: untouched
        self.assertIn(f"{SRV}-other:sha-0000000@{OLD}", new)    # a longer name: untouched

    def test_the_digest_only_shape_keeps_working(self):
        new, n = deploy.bump(f"image: {SRV}@{OLD}\n", SRV, SRV_NEW, "sha-1234567")
        self.assertEqual((n, new), (1, f"image: {SRV}@{SRV_NEW}\n"))

    def test_images_of_a_recipe(self):
        one = {"package": "wordsworth", "image": "ghcr.io/x/wordsworth"}
        self.assertEqual(deploy.images(one), [("wordsworth", "ghcr.io/x/wordsworth")])
        two = {"images": [{"package": "a", "image": "ghcr.io/x/a"},
                          {"package": "b", "image": "ghcr.io/x/b"}]}
        self.assertEqual(deploy.images(two), [("a", "ghcr.io/x/a"), ("b", "ghcr.io/x/b")])


class Road(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = self.t.name
        remote, seed = os.path.join(t, "remote.git"), os.path.join(t, "seed")
        git("init", "-q", "--bare", "-b", "main", remote)
        git("clone", "-q", remote, seed)
        d = os.path.join(seed, "cluster-config/infra/convergence")
        os.makedirs(d)
        open(os.path.join(d, "deployment.yaml"), "w").write(MANIFEST)
        git("add", ".", cwd=seed)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seed", cwd=seed)
        git("push", "-q", "origin", "HEAD:main", cwd=seed)
        self.remote = remote
        self.built = {"convergence-server": SRV_NEW, "convergence-web": WEB_NEW}
        # The deployment lists web BEFORE server: matching must go by name.
        self.running = [f"{WEB}:sha-0000000@{OLD}", f"{SRV}:sha-0000000@{OLD}"]
        cfg = {"owner": "MWest2020",
               "homelab": {"repo_dir": seed, "worktree": os.path.join(t, "wt"), "kubectl": "kubectl"},
               "deploy": {"convergence": {
                   "images": [{"package": "convergence-server", "image": SRV},
                              {"package": "convergence-web", "image": WEB}],
                   "app": "convergence", "namespace": "convergence", "deployment": "convergence",
                   "manifests": ["cluster-config/infra/convergence/deployment.yaml"]}}}
        self.clock = [1000.0]

        def runner(argv, **kw):
            if argv[0] == "gh":
                package = argv[2].split("/container/")[1].split("/")[0]
                rows = ([{"name": self.built[package],
                          "metadata": {"container": {"tags": ["sha-1234567", "main"]}}}]
                        if package in self.built else [])
                return subprocess.CompletedProcess(argv, 0, json.dumps(rows), "")
            if argv[0] == "kubectl":
                if "get" in argv:
                    dep = {"metadata": {"generation": 2}, "spec": {"replicas": 1, "template": {
                        "spec": {"containers": [{"image": i} for i in self.running]}}},
                        "status": {"observedGeneration": 2, "updatedReplicas": 1,
                                   "availableReplicas": 1}}
                    return subprocess.CompletedProcess(argv, 0, json.dumps(dep), "")
                return subprocess.CompletedProcess(argv, 0, "", "")
            return subprocess.run(argv, env=CLEAN, **kw)
        self.d = deploy.Deployer(cfg, runner=runner, now=lambda: self.clock[0])
        self.job = {"repo": "convergence", "issue": 58, "sha": "1234567" + "0" * 33,
                    "phase": "image", "started": 1000.0}

    def tearDown(self):
        self.t.cleanup()

    def test_both_images_go_out_together(self):
        self.assertEqual(self.d.step(self.job)[0], "next")
        self.assertEqual(self.job["digests"], {SRV: SRV_NEW, WEB: WEB_NEW})
        state, msg = self.d.step(self.job)
        self.assertEqual(state, "next", msg)
        check = os.path.join(self.t.name, "check")
        git("clone", "-q", self.remote, check)
        body = open(os.path.join(check, "cluster-config/infra/convergence/deployment.yaml")).read()
        self.assertIn(f"{SRV}:sha-1234567@{SRV_NEW}", body)
        self.assertIn(f"{WEB}:sha-1234567@{WEB_NEW}", body)
        self.assertIn(f"{SRV}-other:sha-0000000@{OLD}", body)
        self.assertEqual(self.d.step(self.job)[0], "next")                 # sync
        self.running = [f"{WEB}:sha-1234567@{WEB_NEW}", f"{SRV}:sha-0000000@{OLD}"]
        self.assertEqual(self.d.step(self.job)[0], "wait")                 # server still old
        self.running = [f"{WEB}:sha-1234567@{WEB_NEW}", f"{SRV}:sha-1234567@{SRV_NEW}"]
        self.assertEqual(self.d.step(self.job)[0], "done")

    def test_one_missing_image_waits_then_fails(self):
        del self.built["convergence-web"]
        self.assertEqual(self.d.step(self.job), ("wait", ""))
        self.assertNotIn("digests", self.job)
        self.clock[0] += deploy.IMAGE_WAIT_S + 1
        state, msg = self.d.step(self.job)
        self.assertEqual(state, "fail")
        self.assertIn("convergence-web", msg)


if __name__ == "__main__":
    unittest.main()
