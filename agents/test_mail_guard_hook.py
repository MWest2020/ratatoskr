# SPDX-License-Identifier: MIT
"""The mail guard as Claude Code runs it: the command from `mail_guard.settings`
through a shell, with a JSON payload on stdin (change odin-mails-mark). A hook
that cannot judge must block (exit 2), never fail open. No mail is sent.
Run from agents/: `python3 -m unittest test_mail_guard_hook`.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import mail_guard as mg

MARK = "mark@westerweel.work"
OK = {"tool_name": mg.SEND, "tool_input": {"to": [MARK], "subject": "s", "htmlBody": "b"}}


def run(cmd, payload=OK, stdin=None, env=None):
    """Claude Code runs a command hook through a shell."""
    p = subprocess.run(["sh", "-c", cmd], input=stdin if stdin is not None else json.dumps(payload),
                       capture_output=True, text=True, timeout=30, env=env)
    out = json.loads(p.stdout)["hookSpecificOutput"] if p.stdout.strip() else None
    return p.returncode, out


class Settings(unittest.TestCase):
    def test_hooks_cannot_be_switched_off_by_a_project_or_user_file(self):
        s = json.loads(mg.settings())
        self.assertIs(s["disableAllHooks"], False)

    def test_a_shell_prefix_cannot_wrap_the_hook(self):
        self.assertEqual(json.loads(mg.settings())["env"], {"CLAUDE_CODE_SHELL_PREFIX": ""})

    def test_every_program_by_absolute_path_and_python_isolated(self):
        words = mg.command().split(" || ")[0].split()
        self.assertEqual(words[0], "/usr/bin/timeout")
        self.assertTrue(os.path.isabs(words[2]) and os.path.isabs(words[4]))
        self.assertEqual(words[3], "-I")

    def test_the_command_is_the_one_in_settings_with_a_deadline_under_the_hooks(self):
        hook = json.loads(mg.settings())["hooks"]["PreToolUse"][0]["hooks"][0]
        self.assertEqual(hook["command"], mg.command())
        self.assertTrue(hook["command"].endswith("|| exit 2"))
        self.assertLess(mg.LIMIT_S, hook["timeout"])


class Judging(unittest.TestCase):
    def test_a_mail_to_mark_is_left_alone(self):
        self.assertEqual(run(mg.command()), (0, None))

    def test_anything_else_is_denied_with_a_reason(self):
        for tool, inp in ((mg.SEND, {"to": ["x@example.org"]}),
                          (mg.SEND, {"to": [MARK], "bcc": ["x@example.org"]}),
                          ("mcp__claude_ai_Gmail__reply", {"messageId": "m", "to": [MARK]}),
                          ("mcp__claude_ai_Gmail__forward", {"messageId": "m", "to": [MARK]})):
            code, out = run(mg.command(), {"tool_name": tool, "tool_input": inp})
            self.assertEqual(code, 0)
            self.assertEqual(out["permissionDecision"], "deny", tool)
            self.assertIn("mail guard", out["permissionDecisionReason"])

    def test_unreadable_input_is_denied(self):
        self.assertEqual(run(mg.command(), stdin="not json")[1]["permissionDecision"], "deny")

    def test_the_matcher_covers_every_gmail_tool(self):
        import re
        self.assertTrue(re.fullmatch(mg.MATCHER, mg.SEND))
        self.assertTrue(re.fullmatch(mg.MATCHER, "mcp__claude_ai_Gmail__forward"))


class FailsClosed(unittest.TestCase):
    """Exit 2 is the only failure Claude Code treats as a block."""

    def script(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_a_missing_interpreter_blocks(self):
        self.assertEqual(run(mg.command(python="/nonexistent/python3"))[0], 2)

    def test_a_moved_script_blocks(self):
        self.assertEqual(run(mg.command(script="/nonexistent/mail_guard.py"))[0], 2)

    def test_a_crashing_script_blocks(self):
        self.assertEqual(run(mg.command(script=self.script("raise SystemExit(1)\n")))[0], 2)
        self.assertEqual(run(mg.command(script=self.script("import no_such_module\n")))[0], 2)

    def test_a_slow_script_blocks(self):
        slow = self.script("import time\ntime.sleep(30)\n")
        self.assertEqual(run(mg.command(script=slow, limit=1))[0], 2)

    def test_a_fake_timeout_or_python_variables_in_the_environment_change_nothing(self):
        evil = tempfile.mkdtemp()
        with open(os.path.join(evil, "timeout"), "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(evil, "timeout"), 0o755)
        with open(os.path.join(evil, "sitecustomize.py"), "w") as f:
            f.write("import sys; sys.exit(0)\n")
        env = dict(os.environ, PATH=f"{evil}:/usr/bin:/bin", PYTHONPATH=evil,
                   PYTHONSTARTUP=os.path.join(evil, "sitecustomize.py"))
        bad = {"tool_name": mg.SEND, "tool_input": {"to": ["x@example.org"]}}
        code, out = run(mg.command(), bad, env=env)
        self.assertEqual((code, out["permissionDecision"]), (0, "deny"))

    def test_a_missing_timeout_blocks(self):
        self.assertEqual(run(mg.command(timeout="/nonexistent/timeout"))[0], 2)

    def test_the_real_interpreter_is_used_by_absolute_path(self):
        self.assertIn(sys.executable, mg.command())


if __name__ == "__main__":
    unittest.main()
