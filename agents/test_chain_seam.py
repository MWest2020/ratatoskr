# SPDX-License-Identifier: MIT
"""Seam test: a merged build's next step is requested through the exact same
`!build` road a chat command takes (AGENTS.md: a seam needs a test that calls
both sides). `build_wiring` and `propose_wiring` are driven together, wired
the way `listener.py` wires them (`late`, for the mutual reference), with
fakes for `gh`, the PR merge check and the habitat chain itself."""
import json
import os
import subprocess
import tempfile
import time
import unittest
from unittest import mock

import build
import build_runner
import build_wiring
import propose_wiring

OWNER, REPO = "MWest2020", "wordsworth"
A_PROPOSAL = "## Next\n`b`\n"
B_PROPOSAL = "## Why\nx\n"


class FakeProc:
    def __init__(self, running=True):
        self.running = running

    def poll(self):
        return None if self.running else 0


class Issues:
    def __init__(self):
        self.created, self.comments = [], []

    def create(self, repo, title, body, labels):
        self.created.append((repo, title))
        return len(self.created), "", ""

    def comment(self, repo, n, body):
        self.comments.append((repo, n, body))
        return ""

    def open_titled(self, repo, title):
        return []


class Merger:
    def checks(self, owner, repo, pr):
        return "merge", "1 check passed"

    def merge(self, owner, repo, pr):
        return ""


class Deployer:
    def recipe(self, repo):
        return None   # no deploy recipe: the merged change archives right away


def fake_gh(proposals, archived=()):
    def runner(argv, **kw):
        joined = " ".join(argv)
        if "proposal.md" in joined:
            change = next(a for a in argv if a.startswith("repos/")).split("/")[6]
            text = proposals.get(change)
            if text is None:
                return subprocess.CompletedProcess(argv, 1, "", "not found")
            return subprocess.CompletedProcess(argv, 0, text, "")
        if "contents/openspec/changes/archive" in joined:
            out = "\n".join(f"2026-11-05-{c}" for c in archived)
            return subprocess.CompletedProcess(argv, 0, out, "")
        if argv[:2] == ["gh", "pr"] and "list" in argv:
            return subprocess.CompletedProcess(argv, 0, "[]", "")
        return subprocess.CompletedProcess(argv, 0, "", "")
    return runner


class Seam(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.said = []
        self.cfg = {"owner": OWNER, "repos": [REPO], "runs": os.path.join(self.tmp.name, "runs"),
                    "max_concurrent": 1, "builds_per_day": 100, "max_builds_per_change_day": 3,
                    "habitat_dir": self.tmp.name, "worker_image": "img:abcdef123456789",
                    "kubectl": "", "logdir": self.tmp.name}
        self.build_issues, self.propose_issues = Issues(), Issues()
        self.builds = build_runner.Builds(self.cfg, popen=lambda *a, **k: FakeProc())
        agents = {"odin": {"nsec": "n", "npub": "p"}}
        send = lambda cid, t, *a: self.said.append((cid, t))  # noqa: E731
        late = {}
        self.try_build, self.build_tick = build_wiring.setup(
            self.cfg, agents, "odin", "mark", send, issues=self.build_issues, log=lambda *a, **k: None,
            builds=self.builds, merger=Merger(), deployer=Deployer(),
            after_merge=lambda m: late["after_merge"](m))
        gh = fake_gh({"a": A_PROPOSAL, "b": B_PROPOSAL})
        (self.try_propose, self.propose_tick, late["after_merge"], self.after_fail, self.after_done) = \
            propose_wiring.setup(
                self.cfg, agents, "odin", send, {}, self.builds, lambda cid: [],
                lambda *a, **k: None, issues=self.propose_issues, log=lambda *a, **k: None,
                archive=lambda *a: (99, ""), gh=gh, try_build=self.try_build)
        self.exists = mock.patch.object(build, "change_exists", lambda *a, **k: ("", True))
        self.exists.start()
        self.addCleanup(self.exists.stop)

    def merge_a(self):
        self.builds.merging.append({"repo": REPO, "change": "a", "issue": 1, "cid": "c",
                                    "cname": "general", "pr": 10, "next": 0})
        self.build_tick()

    def run_file(self, name, change, started):
        with open(os.path.join(self.cfg["runs"], name), "w") as fh:
            fh.write(json.dumps({"repo": REPO, "change": change, "started": started}) + "\n")
            fh.write("[dispatch] Job=habitat-builder-x rol=builder change=" + change + "\n")

    def test_the_merge_of_a_queues_b_through_try_build(self):
        self.merge_a()
        self.assertEqual([b["change"] for b in self.builds.running], ["b"])
        self.assertTrue(any("build started" in t for _, t in self.said))

    def test_with_max_concurrent_reached_b_waits_in_the_queue(self):
        path = os.path.join(self.cfg["runs"], "wordsworth-zzz-1.log")
        open(path, "w").write(json.dumps({"repo": REPO, "change": "zzz", "issue": 2}) + "\n")
        self.builds.running.append({"repo": REPO, "change": "zzz", "issue": 2, "cid": "c2",
                                    "cname": "general", "path": path, "proc": FakeProc(),
                                    "pid": None, "seen": 0})
        self.merge_a()
        self.assertEqual([q["change"] for q in self.builds.queued], ["b"])
        self.assertTrue(any("queued" in t for _, t in self.said))

    def test_with_the_breaker_tripped_the_refusal_is_said(self):
        now = time.time()
        for i in range(3):
            self.run_file(f"wordsworth-b-{i}.log", "b", now)
        self.merge_a()
        self.assertEqual(self.builds.running, [])
        self.assertEqual(self.builds.queued, [])
        self.assertTrue(any("built" in t and "3 times" in t for _, t in self.said))

    def test_odins_own_build_of_b_is_refused_once_the_chain_started_it(self):
        self.merge_a()
        started = len(self.builds.running)
        self.try_build("!build wordsworth b", "odin", "general", "cid2", own=True)
        self.assertEqual(len(self.builds.running), started)   # not a second chain
        self.assertIn("already building or queued", self.said[-1][1])
        self.assertEqual(build.change_builds_today(self.cfg["runs"], REPO, "b", time.time), 1)


if __name__ == "__main__":
    unittest.main()
