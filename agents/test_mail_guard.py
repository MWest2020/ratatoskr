# SPDX-License-Identifier: MIT
"""Offline tests for `mail_guard.py` (Gmail to Mark alone, change odin-mails-mark).
Run from agents/: `python3 -m unittest test_mail_guard`. No mail is sent: the
guard is judged on its own, run as the hook process with a JSON payload, and
the claude command line is captured before anything starts.
"""
import io
import json
import os
import shlex
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock

import agent_turn  # noqa: F401  (the turn imports the guard; it must import cleanly)
import bootstrap
import mail_guard as mg
import providers

MARK = "mark@westerweel.work"
G = "mcp__claude_ai_Gmail__"


def ok(tool, **inp):
    return mg.refusal(tool, inp) == ""


class Refusal(unittest.TestCase):
    def test_a_mail_to_mark_passes(self):
        self.assertTrue(ok(mg.SEND, to=[MARK], subject="Open proposals", htmlBody="<p>x</p>"))
        self.assertTrue(ok(mg.SEND, to=["Mark@Westerweel.Work "], subject="s", body="b"))
        self.assertTrue(ok(mg.SEND, to=MARK, subject="s", body="b", cc=[], bcc=[]))
        self.assertTrue(ok(mg.SEND, to=[MARK], body="b", replyThreadId="t1"))

    def test_a_reply_to_mark_passes(self):
        self.assertTrue(ok(mg.REPLY, messageId="m1", to=[MARK], body="b"))
        self.assertTrue(ok(mg.REPLY, messageId="m1", to=[MARK], body="b", replyAll=False))

    def test_anyone_else_is_refused(self):
        for to in (["someone@example.org"], [MARK, "someone@example.org"], [],
                   ["Mark <mark@westerweel.work>"], ["mark@westerweel.work.evil.org"], None, [5]):
            self.assertFalse(ok(mg.SEND, to=to, subject="s", body="b"), to)

    def test_cc_and_bcc_are_refused_even_to_mark(self):
        self.assertFalse(ok(mg.SEND, to=[MARK], cc=["x@example.org"], body="b"))
        self.assertFalse(ok(mg.SEND, to=[MARK], bcc=["x@example.org"], body="b"))
        self.assertFalse(ok(mg.SEND, to=[MARK], bcc=[MARK], body="b"))
        self.assertFalse(ok(mg.REPLY, messageId="m", to=[MARK], cc=["x@example.org"], body="b"))

    def test_a_draft_or_an_attachment_is_refused(self):
        self.assertFalse(ok(mg.SEND, draftId="d1"))
        self.assertFalse(ok(mg.SEND, to=[MARK], draftId="d1"))   # a draft goes as it is
        self.assertFalse(ok(mg.SEND, to=[MARK], body="b", attachments=[{"content": "eA=="}]))
        self.assertFalse(ok(mg.SEND, to=[MARK], body="b", somethingNew=1))

    def test_a_reply_must_name_mark_and_never_reply_all(self):
        self.assertFalse(ok(mg.REPLY, messageId="m1", body="b"))   # default: the sender
        self.assertFalse(ok(mg.REPLY, messageId="m1", to=["x@example.org"], body="b"))
        self.assertFalse(ok(mg.REPLY, messageId="m1", to=[MARK], replyAll=True, body="b"))

    def test_forward_trash_label_and_drafts_are_refused(self):
        for name in ("forward", "trash_message", "trash_thread", "label_thread",
                     "unlabel_message", "delete_draft", "create_draft", "update_draft",
                     "mark_thread_spam", "delete_label", "get_thread"):
            self.assertFalse(ok(G + name, to=[MARK], messageId="m1"), name)
        self.assertFalse(ok("mcp__claude_ai_Gmail_2__send_message", to=[MARK]))

    def test_other_tools_are_not_its_business(self):
        self.assertTrue(ok("mcp__handbook__read_doc", path="x"))
        self.assertTrue(ok("Read", file_path="x"))

    def test_input_that_is_not_an_object_is_refused(self):
        self.assertNotEqual(mg.refusal(mg.SEND, ["to", MARK]), "")


class Hook(unittest.TestCase):
    """The command `providers.run` wires in, run as Claude Code runs it."""

    def run_hook(self, stdin):
        cmd = json.loads(mg.settings())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        p = subprocess.run(shlex.split(cmd), input=stdin, capture_output=True, text=True,
                           timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)["hookSpecificOutput"] if p.stdout.strip() else None

    def call(self, tool, **inp):
        return self.run_hook(json.dumps({"tool_name": tool, "tool_input": inp}))

    def test_a_mail_to_mark_is_left_alone(self):
        self.assertIsNone(self.call(mg.SEND, to=[MARK], subject="s", htmlBody="<p>b</p>"))

    def test_anything_else_is_denied_with_a_reason(self):
        for tool, inp in ((mg.SEND, {"to": ["x@example.org"]}),
                          (mg.SEND, {"to": [MARK], "bcc": ["x@example.org"]}),
                          (G + "forward", {"messageId": "m", "to": [MARK]})):
            out = self.call(tool, **inp)
            self.assertEqual(out["permissionDecision"], "deny", tool)
            self.assertIn("mail guard", out["permissionDecisionReason"])

    def test_unreadable_input_is_denied(self):
        self.assertEqual(self.run_hook("not json")["permissionDecision"], "deny")

    def test_the_matcher_covers_every_gmail_tool(self):
        import re
        self.assertTrue(re.fullmatch(mg.MATCHER, mg.SEND))
        self.assertTrue(re.fullmatch(mg.MATCHER, G + "forward"))


class Wiring(unittest.TestCase):
    """Definition → build_agents → providers.run → the claude command line."""

    def agents(self, allow):
        d = {"npub": "npub1x", "channels": ["general"], "system": "s", "provider": "claude-p",
             "model": "sonnet", "allow": list(allow), "deny": [], "routes": [], "skills": []}
        with mock.patch.object(bootstrap, "fetch_def", return_value=d), \
             mock.patch.dict(os.environ, {"NSEC_ODIN": "nsec1x"}), \
             redirect_stdout(io.StringIO()) as log:
            got = bootstrap.build_agents({"run": ["odin"]}, "base", {"odin": "npub1x"})
        return got, log.getvalue()

    def cmd(self, allow):
        seen = {}

        def popen(cmd, **kw):
            seen["cmd"] = cmd
            raise OSError("not in a test")
        with mock.patch.object(providers.subprocess, "Popen", popen):
            providers.run("claude-p", "s", "p", allow=allow)
        return seen["cmd"]

    def test_send_and_reply_reach_allowed_tools_and_the_hook_is_on(self):
        agents, _ = self.agents(["Read", mg.SEND, mg.REPLY])
        cmd = self.cmd(agents["odin"]["allow"])
        allowed = cmd[cmd.index("--allowedTools") + 1].split(",")
        self.assertIn(mg.SEND, allowed)
        self.assertIn(mg.REPLY, allowed)
        self.assertEqual(cmd[cmd.index("--settings") + 1], mg.settings())

    def test_the_hook_is_on_for_a_turn_without_mail_too(self):
        self.assertIn("--settings", self.cmd(["Read"]))

    def test_a_definition_with_forward_or_trash_does_not_run(self):
        for tool in (G + "forward", G + "trash_message", G + "create_draft"):
            agents, log = self.agents(["Read", mg.SEND, tool])
            self.assertEqual(agents, {}, tool)
            self.assertIn("Gmail tools other than send/reply", log)

    def test_the_prompt_mentions_mail_only_when_allowed(self):
        self.assertEqual(mg.clause({"allow": ["Read"]}), "")
        text = mg.clause({"allow": ["Read", mg.SEND, mg.REPLY]})
        self.assertIn(MARK, text)
        self.assertIn(mg.SEND, text)
        self.assertIn(mg.REPLY, text)
        self.assertNotIn(mg.REPLY, mg.clause({"allow": [mg.SEND]}))


if __name__ == "__main__":
    unittest.main()
