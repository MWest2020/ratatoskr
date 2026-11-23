# SPDX-License-Identifier: MIT
"""Offline tests for `mail_guard.py` (Gmail to Mark alone, change odin-mails-mark).
Run from agents/: `python3 -m unittest test_mail_guard`. No mail is sent: the
guard is judged on its own, run as the hook process with a JSON payload, and
the claude command line is captured before anything starts.
"""
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import agent_skills
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
        self.assertTrue(ok(mg.SEND, to=["Mark@Westerweel.Work"], subject="s", body="b"))
        self.assertTrue(ok(mg.SEND, to=MARK, subject="s", body="b", cc=[], bcc=[]))

    def test_threading_goes_through_send(self):
        self.assertTrue(ok(mg.SEND, to=[MARK], body="b", replyThreadId="t1"))
        self.assertTrue(ok(mg.SEND, to=[MARK], body="b", replyToMessageId="m1"))

    def test_anyone_else_is_refused(self):
        for to in (["someone@example.org"], [MARK, "someone@example.org"], [],
                   ["Mark <mark@westerweel.work>"], ["mark@westerweel.work.evil.org"], None, [5]):
            self.assertFalse(ok(mg.SEND, to=to, subject="s", body="b"), to)

    def test_lookalikes_and_surrounding_space_are_refused(self):
        for to in ("mar\u212a@westerweel.work",      # KELVIN SIGN lowers to "k"
                   "mark@westerweel.work\u00a0", "\u2003mark@westerweel.work",
                   " mark@westerweel.work", "mark@westerweel.work\n", "mark@westerweel.work\t"):
            self.assertFalse(ok(mg.SEND, to=[to], body="b"), repr(to))

    def test_cc_and_bcc_are_refused_even_to_mark(self):
        self.assertFalse(ok(mg.SEND, to=[MARK], cc=["x@example.org"], body="b"))
        self.assertFalse(ok(mg.SEND, to=[MARK], bcc=["x@example.org"], body="b"))
        self.assertFalse(ok(mg.SEND, to=[MARK], bcc=[MARK], body="b"))

    def test_a_draft_or_an_attachment_is_refused(self):
        self.assertFalse(ok(mg.SEND, draftId="d1"))
        self.assertFalse(ok(mg.SEND, to=[MARK], draftId="d1"))   # a draft goes as it is
        self.assertFalse(ok(mg.SEND, to=[MARK], body="b", attachments=[{"content": "eA=="}]))
        self.assertFalse(ok(mg.SEND, to=[MARK], body="b", somethingNew=1))

    def test_the_reply_tool_is_refused_even_to_mark(self):
        # It may copy the thread's default cc recipients, which the call does not show.
        self.assertFalse(ok(G + "reply", messageId="m1", to=[MARK], body="b"))

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

    def test_send_reaches_allowed_tools_and_the_hook_is_on(self):
        agents, _ = self.agents(["Read", mg.SEND])
        cmd = self.cmd(agents["odin"]["allow"])
        allowed = cmd[cmd.index("--allowedTools") + 1].split(",")
        self.assertIn(mg.SEND, allowed)
        self.assertEqual(cmd[cmd.index("--settings") + 1], mg.settings())

    def test_the_hook_is_on_for_a_turn_without_mail_too(self):
        self.assertIn("--settings", self.cmd(["Read"]))

    def test_a_definition_with_another_sending_tool_does_not_run(self):
        for tool in (G + "reply", G + "forward", G + "trash_message", G + "create_draft",
                     "mcp__slack__send_message", "mcp__outlook__mail_create",
                     "mcp__x__forward_thing", "mcp__x__save_draft"):
            agents, log = self.agents(["Read", mg.SEND, tool])
            self.assertEqual(agents, {}, tool)
            self.assertIn("sending connector tools other than Gmail send_message", log)

    def test_a_definition_with_a_harmless_connector_tool_still_runs(self):
        agents, _ = self.agents(["Read", mg.SEND, "mcp__handbook__read_doc"])
        self.assertIn("odin", agents)

    def test_the_prompt_mentions_mail_only_when_allowed(self):
        self.assertEqual(mg.clause({"allow": ["Read"]}), "")
        text = mg.clause({"allow": ["Read", mg.SEND]})
        self.assertIn(MARK, text)
        self.assertIn(mg.SEND, text)
        self.assertIn("replyThreadId", text)


class Skills(unittest.TestCase):
    """A skill's allowed-tools are pre-approved while it runs: a skill that
    would hand out a sending connector tool is not installed."""

    def install(self, tools):
        import tempfile
        src, root = tempfile.mkdtemp(), tempfile.mkdtemp()
        os.makedirs(os.path.join(src, "s1"))
        with open(os.path.join(src, "s1", "SKILL.md"), "w") as f:
            f.write("---\nname: s1\nallowed-tools:\n" + "".join(f"- {t}\n" for t in tools)
                    + "---\n\n# s1\n")
        got = agent_skills.install({"odin": {"skills": ["s1"]}}, root, source=src,
                                   log=lambda *a, **k: None)
        return got["s1"], os.path.isdir(os.path.join(root, ".claude", "skills", "s1"))

    def test_mail_mark_tools_are_installed(self):
        self.assertEqual(self.install([mg.SEND]), ("", True))

    def test_a_skill_with_reply_or_forward_is_not_installed(self):
        for tool in (G + "reply", G + "forward", "mcp__slack__send_message"):
            reason, installed = self.install([mg.SEND, tool])
            self.assertIn("not installed", reason)
            self.assertFalse(installed, tool)


if __name__ == "__main__":
    unittest.main()
