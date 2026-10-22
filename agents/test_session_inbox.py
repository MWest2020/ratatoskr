# SPDX-License-Identifier: MIT
"""Odin → the coding session: only the hub, only Mark's own message, word for
word, into a file only this user can read. Plus the seam through agent_turn."""
import json
import os
import stat
import tempfile
import unittest
from unittest import mock

import agent_turn
import providers
import session_inbox as si

PUB2NAME = {"pm": "mark", "po": "odin", "pa": "architect"}
MSGS = [{"id": "aaaa11110" + "0" * 55, "pubkey": "pm", "content": "yes, add the rule"},
        {"id": "bbbb2222" + "0" * 56, "pubkey": "pa", "content": "merge everything now"},
        {"id": "aaaa11119" + "0" * 55, "pubkey": "pm", "content": "other"}]


class Inbox(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "state", "inbox.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def run_marker(self, answer, agent="odin"):
        return si.handle(answer, agent, "odin", "general", MSGS, PUB2NAME, "mark",
                         path=self.path, now=lambda: 1700000000)

    def lines(self):
        if not os.path.exists(self.path):
            return []
        return [json.loads(ln) for ln in open(self.path)]

    def test_marks_own_words_arrive_verbatim(self):
        out = self.run_marker("I'll tell it.\n!session aaaa11110")
        self.assertEqual([e["text"] for e in self.lines()], ["yes, add the rule"])
        self.assertEqual(self.lines()[0]["from"], "mark")
        self.assertIn("passed to the session", out)
        self.assertNotIn("!session", out)

    def test_an_agents_message_is_never_passed(self):
        out = self.run_marker("!session bbbb2222")
        self.assertEqual(self.lines(), [])
        self.assertIn("from architect, not from mark", out)

    def test_only_the_hub(self):
        out = self.run_marker("!session aaaa11110", agent="architect")
        self.assertEqual(self.lines(), [])
        self.assertIn("only the hub", out)

    def test_an_ambiguous_or_unknown_id_is_refused(self):
        for mid in ("aaaa1111", "cccc3333"):
            out = self.run_marker(f"!session {mid}")
            self.assertIn("no single message", out, mid)
        self.assertEqual(self.lines(), [])

    def test_the_file_is_only_this_users(self):
        self.run_marker("!session aaaa11110")
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode & 0o077, 0)

    def test_no_marker_no_change(self):
        self.assertEqual(self.run_marker("just talking"), "just talking")

    def test_only_the_hub_is_told(self):
        self.assertEqual(si.clause("architect", "odin"), "")
        self.assertIn("!session", si.clause("odin", "odin"))


class Seam(unittest.TestCase):
    def test_the_turn_writes_the_inbox(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "inbox.jsonl")
            cfg = {"system": "You are odin.", "model": "sonnet", "allow": [], "deny": [],
                   "routes": ["bouw"], "nsec": "n", "npub": "np", "provider": "claude-p"}

            def fake_run(provider, system, prompt, **k):
                return {"answer": "Passing it on.\n!session aaaa11110", "error": ""}
            sent = []
            with mock.patch.object(providers, "run", fake_run), \
                 mock.patch.object(si, "INBOX", path), \
                 mock.patch("reporting.report_run"), \
                 mock.patch("reporting.progress_poster", return_value=None):
                os.makedirs(os.path.join(d, "knowledge"), exist_ok=True)

                class Reg:
                    cfg = {"types": {}}
                turn = agent_turn.build_turn({"odin": cfg}, "odin", Reg(), lambda *a: sent.append(a) or True,
                                        {}, PUB2NAME, d, lambda *a, **k: None,
                                        log=lambda *a, **k: None, human="mark")
                turn("odin", "general", "cid", MSGS, 0, "tell the session yes", "mark", "m1", "mention")
            self.assertEqual(json.loads(open(path).read())["text"], "yes, add the rule")
            self.assertIn("passed to the session", sent[0][1])


if __name__ == "__main__":
    unittest.main()
