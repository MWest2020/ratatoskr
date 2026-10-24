# SPDX-License-Identifier: MIT
"""The API credits (Mark, 2026-10-24): billed work runs on the key, is recorded,
and stops at the month's budget instead of going on. Offline; sops is faked."""
import json
import os
import subprocess
import tempfile
import unittest

import build
import credits


def fake_sops(argv, **kw):
    return subprocess.CompletedProcess(argv, 0, "sk-ant-test-key\n", "")


class Credits(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        open(os.path.join(self.t.name, "channels.yml"), "w").write(
            "channels:\n  convergence: {id: c, billing: api}\n  general: {id: g}\n")
        self.ledger = os.path.join(self.t.name, "ledger.jsonl")
        self.factory = {"api_budget_usd": 10, "api_repos": ["convergence"],
                        "api_max_budget_usd": 1, "max_concurrent_api": 2}
        self.assertEqual(credits.load(self.t.name, self.factory, run=fake_sops), "")

    def tearDown(self):
        credits._state.update(key="", budget=0.0, channels=set(), repos=set())
        self.t.cleanup()

    def test_scope(self):
        self.assertTrue(credits.channel_billed("convergence"))
        self.assertFalse(credits.channel_billed("general"))
        self.assertTrue(credits.repo_billed("MWest2020/convergence"))
        self.assertFalse(credits.repo_billed("wordsworth"))

    def test_the_key_goes_only_where_asked(self):
        self.assertEqual(credits.env({"PATH": "/bin"})["ANTHROPIC_API_KEY"], "sk-ant-test-key")
        self.assertNotIn("ANTHROPIC_API_KEY", {"PATH": "/bin"})

    def test_the_budget_stops_billed_work(self):
        credits.record("turn", 4.0, "a", ledger=self.ledger)
        self.assertEqual(credits.refusal(ledger=self.ledger), "")
        credits.record("build-role", 6.5, "b", ledger=self.ledger)
        self.assertIn("used up", credits.refusal(ledger=self.ledger))

    def test_last_month_does_not_count(self):
        with open(self.ledger, "w") as fh:
            fh.write(json.dumps({"ts": 0, "cost": 99}) + "\n")
        self.assertEqual(credits.spent(ledger=self.ledger), 0.0)

    def test_no_key_no_billed_work(self):
        credits._state["key"] = ""
        self.assertIn("not loaded", credits.refusal(ledger=self.ledger))


class BilledBuilds(Credits):
    def test_api_chains_run_side_by_side_and_skip_the_day_cap(self):
        cfg = {"repos": ["convergence", "wordsworth"], "owner": "MWest2020",
               "runs": self.t.name, "max_concurrent": 1, "builds_per_day": 0,
               **self.factory}
        gh = lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "[]", "")  # noqa: E731
        orig = credits.LEDGER
        credits.LEDGER = self.ledger
        try:
            ok = build.check(cfg, "convergence", "x", [{"repo": "wordsworth"}], gh)
            self.assertEqual(ok[0], "convergence")      # the subscription chain does not block it
            full = build.check(cfg, "convergence", "x",
                               [{"repo": "convergence"}, {"repo": "convergence"}], gh)
            self.assertIn("API-billed chains", full[1])
            self.assertIn("day", build.check(cfg, "wordsworth", "x", [], gh)[1])
        finally:
            credits.LEDGER = orig


class Queue(Credits):
    """2026-10-24: with three billed chains running, a fourth build was refused
    and dropped; it now waits in a queue and starts when a slot frees."""

    def test_a_full_house_queues_and_drains(self):
        import build_runner
        import build_wiring
        said, started = [], []
        cfg = {"repos": ["convergence"], "owner": "MWest2020", "runs": self.t.name,
               "max_concurrent": 1, "builds_per_day": 0, "worker_image": "img:abc",
               **self.factory}
        builds = build_runner.Builds(cfg, popen=None)
        builds.start = lambda *a: started.append(a[1]) or {"path": "p"}
        builds.tick = lambda on_event: None
        builds.running = [{"repo": "convergence", "change": "a"}, {"repo": "convergence", "change": "b"}]

        class Issues:
            def create(self, *a):
                return 9, "u", ""

            def comment(self, *a):
                return ""
        orig_ok, orig_ledger = build.change_exists, credits.LEDGER
        build.change_exists = lambda *a: ("", True)
        credits.LEDGER = self.ledger            # never the real month's spend
        try:
            try_build, tick = build_wiring.setup(cfg, {"odin": {"nsec": "n", "npub": "p"}}, "odin",
                                                 "mark", lambda cid, t, *a: said.append(t),
                                                 issues=Issues(), builds=builds,
                                                 log=lambda *a, **k: None)
            try_build("!build convergence c 7", "odin", "convergence", "cid", own=True)
            self.assertIn("queued", said[-1])
            try_build("!build convergence c 7", "odin", "convergence", "cid", own=True)
            self.assertIn("already building or queued", said[-1])
            builds.running = builds.running[:1]        # a chain finished
            tick()
            self.assertEqual(started, ["c"])
            self.assertEqual(builds.queued, [])
        finally:
            build.change_exists, credits.LEDGER = orig_ok, orig_ledger


if __name__ == "__main__":
    unittest.main()
