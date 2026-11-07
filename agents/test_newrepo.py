# SPDX-License-Identifier: MIT
"""`!newrepo` (Mark, 2026-11-07: "odin moet dat wel kunnen"), offline: which
markers count, what is refused, that only a created repository joins the lists,
and the wiring for odin and Mark. GitHub and git are faked."""
import os
import subprocess
import tempfile
import unittest

import factory_wiring as fw
import newrepo
import propose_marker


class Fake:
    """A runner: `gh api repos/...` answers per `exists`; everything else passes."""

    def __init__(self, exists=False, fail=None):
        self.exists, self.fail, self.calls = exists, fail, []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        if self.fail and self.fail in argv:
            return subprocess.CompletedProcess(argv, 1, "", f"{self.fail} broke")
        if argv[:2] == ["gh", "api"]:
            if self.exists is None:
                return subprocess.CompletedProcess(argv, 1, "", "HTTP 502")
            if self.exists:
                return subprocess.CompletedProcess(argv, 0, "MWest2020/x", "")
            return subprocess.CompletedProcess(argv, 1, "", "gh: Not Found (HTTP 404)")
        if argv[:2] == ["git", "clone"]:
            os.makedirs(argv[-1], exist_ok=True)
        return subprocess.CompletedProcess(argv, 0, "", "")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.tmp.name, "created.json")
        self.cfg = {"owner": "MWest2020", "repos": ["ratatoskr"], "readable": ["ratatoskr"],
                    "new_repos_per_day": 2}

    def tearDown(self):
        self.tmp.cleanup()

    def act(self, name, runner, now=lambda: 1_800_000_000):
        return newrepo.act(self.cfg, name, "A game.", "odin", runner, now, self.state,
                           home=self.tmp.name)


class Marker(unittest.TestCase):
    def test_first_line_only_for_odin_any_line_for_mark(self):
        self.assertEqual(newrepo.read_marker("!newrepo bubbels2 Ad-free game\nok"),
                         ("bubbels2", "Ad-free game"))
        self.assertIsNone(newrepo.read_marker("so:\n!newrepo bubbels2 Ad-free game"))
        self.assertEqual(newrepo.read_marker("so:\n!newrepo bubbels2 Ad-free game", own=False),
                         ("bubbels2", "Ad-free game"))

    def test_a_marker_that_does_not_parse_is_said(self):
        self.assertIn("not understood", newrepo.unread("!newrepo bubbels2"))
        self.assertIn("not understood", newrepo.unread("!newrepo b@d name here"))
        self.assertEqual(newrepo.unread("!newrepo bubbels2 A game"), "")
        self.assertEqual(newrepo.unread("hello"), "")

    def test_a_leading_newrepo_line_may_precede_the_propose_block(self):
        ans = "!newrepo bubbels2 A game\n!propose bubbels2 core The core.\nwhy"
        self.assertEqual(propose_marker.read_markers(ans), [("bubbels2", "core", "The core.")])
        self.assertEqual(propose_marker.strip_markers(ans), "why")


class Checks(Base):
    def test_existing_repo_refused(self):
        out = self.act("wordsworth", Fake(exists=True))
        self.assertIn("repo not created: `MWest2020/wordsworth` exists already", out)
        self.assertNotIn("wordsworth", self.cfg["repos"])
        self.assertEqual(newrepo.load(self.state), [])

    def test_alma_and_conduction_refused_without_asking_github(self):
        for name in ("alma", "Conduction-tools"):
            fake = Fake()
            self.assertIn("never creates", self.act(name, fake))
            self.assertEqual(fake.calls, [])

    def test_day_cap(self):
        self.assertIn("repo created", self.act("one", Fake()))
        self.assertIn("repo created", self.act("two", Fake()))
        out = self.act("three", Fake())
        self.assertIn("limit of 2 new repositories", out)
        tomorrow = self.act("three", Fake(), now=lambda: 1_800_000_000 + 86400)
        self.assertIn("repo created", tomorrow)

    def test_github_unreachable_is_a_refusal_not_a_guess(self):
        self.assertIn("could not ask GitHub", self.act("x2", Fake(exists=None)))


class Create(Base):
    def test_private_bootstrapped_over_ssh_recorded_and_listed(self):
        fake = Fake()
        out = self.act("bubbels2", fake)
        self.assertIn("📦 repo created: MWest2020/bubbels2 (private)", out)
        create = next(c for c in fake.calls if c[:3] == ["gh", "repo", "create"])
        self.assertIn("--private", create)
        self.assertIn(["git", "remote", "add", "origin", "git@github.com:MWest2020/bubbels2.git"],
                      fake.calls)
        self.assertTrue(any(c[:3] == ["gh", "label", "create"] and "build" in c for c in fake.calls))
        self.assertTrue(os.path.isdir(os.path.join(self.tmp.name, "bubbels2")))
        self.assertIn("bubbels2", self.cfg["repos"])
        self.assertIn("bubbels2", self.cfg["readable"])
        self.assertEqual(newrepo.load(self.state)[0]["by"], "odin")

    def test_a_failed_create_records_nothing(self):
        out = self.act("bubbels2", Fake(fail="create"))
        self.assertIn("repo not created: gh repo create failed", out)
        self.assertEqual(newrepo.load(self.state), [])
        self.assertNotIn("bubbels2", self.cfg["repos"])

    def test_a_failed_push_still_records_and_says_what_is_missing(self):
        out = self.act("bubbels2", Fake(fail="push"))
        self.assertIn("repo created", out)
        self.assertIn("bootstrap stopped at `git push", out)
        self.assertIn("bubbels2", self.cfg["repos"])

    def test_template_renders_every_placeholder(self):
        dst = os.path.join(self.tmp.name, "out")
        newrepo.render(dst, "bubbels2", 'A "quoted" game', "odin", "2026-11-07")
        for root, _, files in os.walk(dst):
            for f in files:
                text = open(os.path.join(root, f)).read()
                self.assertNotIn("{{", text, f)
        self.assertTrue(os.access(os.path.join(dst, "verify.sh"), os.X_OK))
        self.assertTrue(os.path.exists(os.path.join(dst, ".github", "workflows", "verify.yml")))

    def test_merge_known_only_adds_recorded_names_once(self):
        newrepo.record({"name": "bubbels2", "ts": 1}, self.state)
        newrepo.merge_known(self.cfg, self.state)
        newrepo.merge_known(self.cfg, self.state)
        self.assertEqual(self.cfg["repos"], ["ratatoskr", "bubbels2"])


class Wiring(Base):
    def setUp(self):
        super().setUp()
        self.said, self.acted = [], []
        test = self

        class Repos:
            read_marker = staticmethod(newrepo.read_marker)
            unread = staticmethod(newrepo.unread)
            merge_known = staticmethod(lambda cfg: None)

            @staticmethod
            def act(cfg, name, desc, starter):
                test.acted.append((name, starter))
                return f"📦 repo created: {name}"
        agents = {"odin": {"nsec": "n", "npub": "p"}}
        self.marker, self.yes, _ = fw.setup(
            agents, "odin", "mark", lambda cid, t, *a: self.said.append(t), {}, self.tmp.name,
            "base", cfg=self.cfg, repos=Repos, log=lambda *a, **k: None)

    def test_odin_first_line_and_mark_anywhere(self):
        self.marker("!newrepo bubbels2 A game", "odin", "general", "c")
        self.marker("!newrepo other A game", "architect", "general", "c")
        self.yes("ok\n!newrepo marks A game", "mark", "c")
        self.yes("!newrepo nope A game", "architect", "c")
        self.assertEqual(self.acted, [("bubbels2", "odin"), ("marks", "mark")])

    def test_unparsed_marker_from_odin_is_said(self):
        self.marker("!newrepo bubbels2", "odin", "general", "c")
        self.assertIn("not understood", self.said[-1])


if __name__ == "__main__":
    unittest.main()
