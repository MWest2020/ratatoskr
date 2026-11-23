# SPDX-License-Identifier: MIT
"""Offline tests for `turn_settings.py`: a listener tree whose `.claude`
settings could route around the mail guard runs no turn (change
odin-mails-mark, security review of #256). Run from agents/:
`python3 -m unittest test_turn_settings`.
"""
import json
import os
import tempfile
import unittest
from unittest import mock

import providers
import reporting
import turn_settings as ts


def tree(files):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".claude", "skills"))
    for name, data in files.items():
        with open(os.path.join(d, ".claude", name), "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
    return d


class Problem(unittest.TestCase):
    def test_no_settings_or_harmless_ones_are_fine(self):
        self.assertIsNone(ts.problem(tree({})))
        self.assertIsNone(ts.problem(tree({"settings.json": {"model": "sonnet",
                                           "permissions": {"deny": ["Write"], "allow": []}}})))

    def test_anything_that_runs_or_widens_is_refused(self):
        for data in ({"env": {"PATH": "/evil:/usr/bin"}},
                     {"env": {"CLAUDE_CODE_SHELL_PREFIX": "/evil/prefix"}},
                     {"env": {"LD_PRELOAD": "/evil.so"}}, {"env": {"BASH_ENV": "/evil"}},
                     {"hooks": {}}, {"disableAllHooks": True}, {"apiKeyHelper": "x"},
                     {"enableAllProjectMcpServers": True}, {"statusLine": {}},
                     {"permissions": {"defaultMode": "bypassPermissions"}},
                     {"permissions": "all"}, {"somethingNew": 1}):
            for name in ts.SETTINGS_FILES:
                self.assertIsNotNone(ts.problem(tree({name: data})), (name, data))

    def test_a_file_that_is_not_a_json_object_is_refused(self):
        for raw in ("not json", "[]", "x" * (ts.MAX_BYTES + 10)):
            self.assertIsNotNone(ts.problem(tree({"settings.local.json": raw})))

    def test_a_symlink_is_refused(self):
        d = tree({})
        target = os.path.join(tempfile.mkdtemp(), "s.json")
        open(target, "w").write("{}")
        os.symlink(target, os.path.join(d, ".claude", "settings.json"))
        self.assertIn("symlink", ts.problem(d))
        d2 = tempfile.mkdtemp()
        os.symlink(tempfile.mkdtemp(), os.path.join(d2, ".claude"))
        self.assertIn("symlink", ts.problem(d2))

    def test_the_users_own_settings_are_not_a_projects(self):
        d = tree({"settings.json": {"env": {"X": "1"}, "hooks": {}}})
        self.assertIsNone(ts.problem(d, user_dir=os.path.join(d, ".claude")))


class Turn(unittest.TestCase):
    def test_a_turn_beside_unsafe_settings_never_starts(self):
        d = tree({"settings.local.json": {"env": {"CLAUDE_CODE_SHELL_PREFIX": "/evil"}}})
        cwd = os.getcwd()
        popen = mock.Mock(side_effect=AssertionError("claude must not start"))
        try:
            os.chdir(d)
            with mock.patch.object(providers.subprocess, "Popen", popen):
                r = providers.run("claude-p", "s", "p", allow=["Read"])
        finally:
            os.chdir(cwd)
        popen.assert_not_called()
        self.assertTrue(r["error"].startswith("unsafe settings"))
        self.assertIn("sets env", r["error"])

    def test_the_refusal_goes_to_escalatie_with_its_reason(self):
        sent = []
        r = {"answer": "(refused)", "error": "unsafe settings: /x/.claude/settings.json sets env",
             "denials": [], "model": "", "cost": 0.0, "turns": 0}
        reporting.report_run(lambda cid, text, *a: sent.append((cid, text)),
                             {"escalatie": "esc"}, "odin", "general",
                             {"nsec": "n", "npub": "p"}, r)
        self.assertEqual(sent[0][0], "esc")
        self.assertIn("sets env", sent[0][1])
        self.assertIn("turn_settings.py", sent[0][1])

    def test_the_listener_tree_itself_is_clean(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertIsNone(ts.problem(root))


if __name__ == "__main__":
    unittest.main()
