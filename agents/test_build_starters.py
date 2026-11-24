# SPDX-License-Identifier: MIT
"""Who may start a build from the chat (build_starters.py), through the real
build road (build_wiring.try_build) with GitHub and the chain faked.

Mark, 2026-11-14: "claude, odin, or jarvis mogen dit." The list lives in
factory.yml; an agent's marker counts on its first line only, and an agent's
message is never answered as chat."""
import os
import tempfile
import unittest
from unittest import mock

import yaml

import build
import build_runner
import build_starters
import build_wiring
from test_build import CHAIN_LOG, FakeProc, cfg

HERE = os.path.dirname(os.path.abspath(__file__))
STARTERS = ["mark", "odin", "claude", "jarvis", "heimdall"]  # heimdall: 2026-11-24


class RoadFixture:
    """The poll loop's road: take() in front of the real try_build. A mixin, not a
    TestCase, so test_build_starters_echo.py can reuse it without running these twice."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.said, self.calls, self.argv = [], [], []
        self.cfg = cfg(self.tmp.name, build_starters=STARTERS)

        class Issues:
            def create(s, repo, title, body, labels):
                self.calls.append(("create", repo, title, body))
                return 7, "u", ""

            def comment(s, repo, n, body):
                self.calls.append(("comment", repo, n, body))
                return ""

        def popen(argv, **kw):
            self.argv.append(argv)
            kw["stdout"].write(CHAIN_LOG.format(store="/nowhere"))
            kw["stdout"].flush()
            return FakeProc(code=None)
        self.builds = build_runner.Builds(self.cfg, popen=popen)
        self.try_build, _ = build_wiring.setup(
            self.cfg, {"odin": {"nsec": "n", "npub": "np"}}, "odin", "mark",
            lambda cid, t, *a: self.said.append(t), issues=Issues(),
            log=lambda *a, **k: None, builds=self.builds)
        for name, fake in (("change_exists", ("", True)), ("open_issue", True)):
            p = mock.patch.object(build, name, lambda *a, f=fake, **k: f)
            p.start()
            self.addCleanup(p.stop)

        self.refused, self.logged, self.t = {}, [], [1000.0]

    def take(self, writer, content, own_posts=None, ids=None):
        return build_starters.take({"content": content}, writer, "escalatie", "cid",
                                   self.try_build, self.cfg, "odin", "mark", own_posts,
                                   ids=ids, refused=self.refused, now=lambda: self.t[0],
                                   log=lambda *a, **k: self.logged.append(a[0]))


class Road(RoadFixture, unittest.TestCase):

    def test_an_allowed_agents_first_line_marker_starts_a_build(self):
        self.assertTrue(self.take("claude", "!build ratatoskr x\nwhy: the spec is merged"))
        self.assertEqual(len(self.argv), 1)
        create = next(c for c in self.calls if c[0] == "create")
        self.assertIn("started by **claude**", create[3])     # the starter on the issue
        self.assertTrue(any(c[0] == "comment" and "Build started by **claude**" in c[3]
                            for c in self.calls))
        self.assertIn("build started", self.said[-1])

    def test_a_session_pinging_as_odin_starts_one_too(self):
        self.assertTrue(self.take("odin", "!build ratatoskr x 12"))
        self.assertEqual(len(self.argv), 1)
        self.assertIn("ratatoskr#12", self.said[-1])

    def test_an_agents_marker_not_on_the_first_line_does_nothing(self):
        self.assertTrue(self.take("jarvis", "quote:\n!build ratatoskr x"))   # still not chat
        self.assertEqual((self.argv, self.calls, self.said), ([], [], []))

    def test_an_agent_not_on_the_list_is_ignored(self):
        self.assertFalse(self.take("hubby", "!build ratatoskr x"))   # caller: as before
        self.assertFalse(self.take("architect", "!build ratatoskr x"))
        self.assertEqual((self.argv, self.said), ([], []))

    def test_off_the_list_through_try_build_is_refused_aloud(self):
        self.try_build("!build ratatoskr x", "architect", "general", "cid", own=True)
        self.assertEqual(self.argv, [])
        self.assertIn("⛔ build not started: only mark, odin, claude, jarvis or heimdall", self.said[-1])

    def test_marks_message_keeps_its_own_road(self):
        self.assertFalse(self.take("mark", "!build ratatoskr x"))   # the listener's path
        self.assertEqual(self.argv, [])
        self.try_build("go ahead\n!build ratatoskr x", "mark", "general", "cid", own=False)
        self.assertEqual(len(self.argv), 1)                          # anywhere, as before

    def test_an_agent_starter_is_capped_like_odin(self):
        with mock.patch.object(build, "check", return_value=(None, "budget")) as chk:
            self.take("claude", "!build ratatoskr x")
        self.assertTrue(chk.call_args.kwargs["capped"])


class NoChat(unittest.TestCase):
    def test_an_allowed_agents_message_is_never_answered_as_chat(self):
        seen = []
        stop = build_starters.take({"content": "hello odin, how are you"}, "claude", "c",
                                   "cid", lambda *a, **k: seen.append(a),
                                   {"build_starters": STARTERS}, "odin", "mark", refused={})
        self.assertTrue(stop)
        self.assertEqual(seen, [((("hello odin, how are you", "claude", "c", "cid")))])

    def test_the_listener_stops_before_any_chat_road(self):
        """The seam: take() runs before the agent filter, sessions, rooms and triggers,
        and a True means `continue`."""
        with open(os.path.join(HERE, "listener.py")) as fh:
            src = fh.read().splitlines()
        at = next(i for i, ln in enumerate(src) if "build_starters.take(" in ln)
        self.assertIn("continue", src[at + 1])
        for later in ("in AGENT_PUBS", "try_session(content", "room(cname", "triggers.pick("):
            self.assertLess(at, next(i for i, ln in enumerate(src) if later in ln), later)


class TheList(unittest.TestCase):
    def test_without_the_key_only_hub_and_human(self):
        self.assertEqual(build_starters.allowed({}, "odin", "mark"), ["odin", "mark"])
        self.assertEqual(build_starters.who({}, "odin", "mark"), "odin or mark")

    def test_a_revoked_key_starts_nothing(self):
        ids = {n: dict(v) for n, v in build_starters.identities().items()}
        ids["jarvis"]["status"] = "ingetrokken"
        c = {"build_starters": STARTERS}
        self.assertEqual(build_starters.allowed(c, "odin", "mark", ids), ["mark", "odin", "claude", "heimdall"])
        self.assertEqual(build_starters.who(c, "odin", "mark", ids), "mark, odin, claude or heimdall")
        seen = []
        self.assertFalse(build_starters.take({"content": "!build ratatoskr x"}, "jarvis", "c",
                                             "cid", lambda *a, **k: seen.append(a), c,
                                             "odin", "mark", ids=ids, refused={}))
        self.assertEqual(seen, [])

    def test_factory_yml_names_identities_that_exist(self):
        """The seam between factory.yml and identities.yml: a name on the list with
        no identity could never match a pubkey."""
        with open(os.path.join(HERE, "factory.yml")) as fh:
            f = yaml.safe_load(fh)
        with open(os.path.join(HERE, "..", "identities.yml")) as fh:
            ids = yaml.safe_load(fh)["identities"]
        self.assertEqual(f["build_starters"], STARTERS)
        for name in f["build_starters"]:
            self.assertIn(name, ids, name)
            self.assertEqual(ids[name].get("status"), "actief", name)


if __name__ == "__main__":
    unittest.main()
