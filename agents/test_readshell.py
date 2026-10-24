# SPDX-License-Identifier: MIT
"""The read shell (change odin-read-shell): what it accepts, the one command it
runs per question, and how it fails. Plus the seam: a definition that allows
the rule reaches `--allowedTools` unchanged, and one with a free Bash does not
run at all. Offline: gh is never called."""
import io
import os
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock

import bootstrap
import providers
import readshell as rs


def parse(*args):
    return rs.parser().parse_args(list(args))


def refused(*args):
    with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
        try:
            parse(*args)
        except SystemExit as e:
            return e.code != 0
    return False


class Arguments(unittest.TestCase):
    def test_the_owner_is_fixed(self):
        self.assertEqual(parse("prs", "wordsworth").repo, "MWest2020/wordsworth")

    def test_crafted_repository_names_are_refused(self):
        for bad in ("other/repo", "../x", "-x", "a..b", "", "x y", "x;id", "$(id)"):
            self.assertTrue(refused("prs", bad), bad)

    def test_numbers_are_bounded(self):
        self.assertEqual(parse("log", "ratatoskr", "5").n, 5)
        for bad in ("0", "41", "-1", "1e3", "x"):
            self.assertTrue(refused("log", "ratatoskr", bad), bad)

    def test_a_label_cannot_be_a_flag(self):
        self.assertTrue(refused("issues", "wordsworth", "--repo=evil/x"))
        self.assertEqual(parse("issues", "wordsworth", "agent-work").label, "agent-work")

    def test_unknown_subcommands_are_refused(self):
        for bad in ("api", "merge", "clone"):
            self.assertTrue(refused(bad, "wordsworth"), bad)


class Commands(unittest.TestCase):
    def test_every_command_is_a_read(self):
        reads = {("api",), ("pr", "list"), ("issue", "list"), ("pr", "checks")}
        for cmd, extra in (("log", ()), ("branches", ()), ("changes", ()), ("prs", ()),
                           ("issues", ("agent-work",)), ("checks", ("42",))):
            a = rs.argv(parse(cmd, "wordsworth", *extra))
            self.assertEqual(a[0], "gh")
            self.assertTrue(tuple(a[1:2]) in reads or tuple(a[1:3]) in reads, a)
            self.assertNotIn("-X", a)
            self.assertNotIn("--method", " ".join(a))

    def test_api_paths_stay_on_the_owner(self):
        a = rs.argv(parse("log", "wordsworth", "3"))
        self.assertEqual(a[2], "repos/MWest2020/wordsworth/commits?per_page=3")

    def test_flags_carry_their_value_with_an_equals_sign(self):
        a = rs.argv(parse("issues", "wordsworth", "needs-mark"))
        self.assertIn("--repo=MWest2020/wordsworth", a)
        self.assertEqual(a[-1], "--label=needs-mark")


def fake(stdout="", stderr="", code=0):
    def runner(argv, **kw):
        return subprocess.CompletedProcess(argv, code, stdout, stderr)
    return runner


def output(a, runner):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = rs.run(a, runner)
    return code, buf.getvalue()


class Running(unittest.TestCase):
    def test_output_is_capped_and_says_so(self):
        code, out = output(parse("branches", "x"), fake("\n".join(map(str, range(100)))))
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), rs.MAX_LINES + 1)
        self.assertIn("60 more lines", out)

    def test_a_failure_says_why(self):
        code, out = output(parse("changes", "x"), fake("", "HTTP 404: Not Found\nmore", 1))
        self.assertEqual(code, 1)
        self.assertIn("changes MWest2020/x failed: HTTP 404: Not Found", out)

    def test_empty_is_not_silent(self):
        code, out = output(parse("prs", "x"), fake(""))
        self.assertEqual(code, 0)
        self.assertIn("none", out)

    def test_pending_checks_still_answer(self):
        code, out = output(parse("checks", "x", "7"), fake("build\tpending\n", "", 8))
        self.assertEqual(code, 0)
        self.assertIn("pending", out)

    def test_a_timeout_says_so(self):
        def slow(argv, **kw):
            raise subprocess.TimeoutExpired(argv, rs.TIMEOUT_S)
        code, out = output(parse("log", "x"), slow)
        self.assertEqual(code, 1)
        self.assertIn("timed out", out)


class Mandate(unittest.TestCase):
    def test_only_the_rule_is_allowed_bash(self):
        self.assertEqual(rs.stray_bash(["Read", rs.RULE]), [])
        self.assertEqual(rs.stray_bash(["Read", "Bash"]), ["Bash"])
        self.assertEqual(rs.stray_bash(["Bash(gh pr list:*)"]), ["Bash(gh pr list:*)"])

    def test_the_prompt_mentions_the_shell_only_when_allowed(self):
        self.assertEqual(rs.clause({"allow": ["Read", "Grep"]}), "")
        text = rs.clause({"allow": ["Read", rs.RULE]})
        self.assertIn("python3 agents/readshell.py prs <repo>", text)


class Seam(unittest.TestCase):
    """Definition → build_agents → providers.run → the claude command line."""

    def agents(self, allow, deny=()):
        d = {"npub": "npub1x", "channels": ["general"], "system": "s", "provider": "claude-p",
             "model": "sonnet", "allow": list(allow), "deny": list(deny),
             "routes": [], "skills": []}
        with mock.patch.object(bootstrap, "fetch_def", return_value=d), \
             mock.patch.dict(os.environ, {"NSEC_ODIN": "nsec1x"}), \
             redirect_stdout(io.StringIO()) as log:
            got = bootstrap.build_agents({"run": ["odin"]}, "base", {"odin": "npub1x"})
        return got, log.getvalue()

    def test_the_rule_reaches_allowed_tools_unchanged(self):
        agents, _ = self.agents(["Read", "Grep", "Glob", rs.RULE], ["Write", "Edit"])
        cfg = agents["odin"]
        seen = {}

        def popen(cmd, **kw):
            seen["cmd"] = cmd
            raise OSError("not in a test")
        with mock.patch.object(providers.subprocess, "Popen", popen):
            providers.run("claude-p", "s", "p", allow=cfg["allow"], deny=cfg["deny"])
        allowed = seen["cmd"][seen["cmd"].index("--allowedTools") + 1].split(",")
        self.assertIn(rs.RULE, allowed)
        self.assertIn("Read(./**)", allowed)

    def test_a_free_shell_does_not_run(self):
        agents, log = self.agents(["Read", "Bash"])
        self.assertEqual(agents, {})
        self.assertIn("Bash other than the read shell", log)

    def test_rule_with_bash_denied_is_logged(self):
        agents, log = self.agents(["Read", rs.RULE], ["Bash"])
        self.assertIn("odin", agents)
        self.assertIn("deny wins", log)


if __name__ == "__main__":
    unittest.main()


class Comments(unittest.TestCase):
    def test_the_last_comments_of_one_issue(self):
        a = rs.parser().parse_args(["comments", "wordsworth", "219", "2"])
        cmd = rs.argv(a)
        self.assertEqual(cmd[:5], ["gh", "issue", "view", "219", "--repo=MWest2020/wordsworth"])
        self.assertTrue(cmd[-1].startswith(".comments[-2:][]"))

    def test_a_number_is_required(self):
        with self.assertRaises(SystemExit):
            rs.parser().parse_args(["comments", "wordsworth", "x"])
