# SPDX-License-Identifier: MIT
"""The propose marker's limits and amending an existing change (split from
test_propose.py for the line limit)."""
import os
import subprocess
import tempfile
import unittest

import propose
from test_propose import Builds, Proc, Wiring


class LongSummary(unittest.TestCase):
    """2026-10-24: odin's summaries ran to ~400 characters and were dropped."""
    LONG = "!propose wordsworth pilot-ingest-manifest " + "Extend the ingest. " * 20

    def test_a_long_summary_is_read(self):
        self.assertEqual(propose.read_marker(self.LONG)[1], "pilot-ingest-manifest")

    def test_a_line_that_does_not_parse_is_said(self):
        self.assertIn("not understood", propose.unread("!propose wordsworth X Bad id."))
        self.assertEqual(propose.unread(self.LONG), "")
        self.assertEqual(propose.unread("no marker"), "")


class Amend(unittest.TestCase):
    """2026-10-24: a build stopped on an open question and reviewer findings,
    and an existing change could not be amended. Now it can, by the same marker."""

    def start(self, exists):
        import io
        with tempfile.TemporaryDirectory() as wt:
            if exists:
                os.makedirs(os.path.join(wt, "openspec", "changes", "add-x"))
            fed = io.StringIO()

            class P:
                pid = 1
                stdin = fed
            fed.close = lambda: None
            job, why = propose.start("/clone", "add-x", "Settle: WORDSWORTH_BACKEND_ENV.", [], {},
                                     "odin", popen=lambda *a, **k: P(),
                                     create=lambda *a: (wt, "b"))
            return job, why, fed.getvalue()

    def test_an_existing_change_is_amended(self):
        job, why, prompt = self.start(exists=True)
        self.assertEqual(why, "")
        self.assertTrue(job["amend"])
        self.assertIn("ALREADY EXISTS on main: AMEND it", prompt)

    def test_a_new_change_is_written(self):
        job, why, prompt = self.start(exists=False)
        self.assertFalse(job["amend"])
        self.assertNotIn("AMEND", prompt)

    def test_the_pr_says_amend(self):
        calls = []

        def run(argv, **kw):
            calls.append(argv)
            out = "https://github.com/o/r/pull/7\n" if argv[0] == "gh" else ""
            return subprocess.CompletedProcess(argv, 0, out, "")
        n, err = propose.publish({"wt": "/w", "change": "add-x", "branch": "b", "summary": "s",
                                  "amend": True}, "r", "o", run)
        self.assertEqual((n, err), (7, ""))
        self.assertIn("--title=openspec: amend add-x", calls[-1])

    def test_odin_is_told_how_to_amend(self):
        self.assertIn("EXISTING change id amends", propose.clause("odin", "odin"))



class RefusedWrites(unittest.TestCase):
    """2026-10-24: two amend sessions had every Edit inside the fence refused,
    and the same run again worked. Those refusals are named and retried once."""

    def test_only_writes_inside_the_fence_count(self):
        import json
        with tempfile.TemporaryDirectory() as wt:
            inside = f"{wt}/openspec/changes/add-x/tasks.md"
            res = {"type": "result", "permission_denials": [
                {"tool_name": "Edit", "tool_input": {"file_path": inside}},
                {"tool_name": "Bash", "tool_input": {"command": "python3 -"}},
                {"tool_name": "Edit", "tool_input": {"file_path": f"{wt}/src/x.py"}}]}
            open(os.path.join(wt, ".propose-run.jsonl"), "w").write(json.dumps(res) + "\n")
            self.assertEqual(propose.refused_writes({"wt": wt, "change": "add-x"}), [inside])

    def test_no_run_file_no_refusals(self):
        self.assertEqual(propose.refused_writes({"wt": "/nonexistent", "change": "x"}), [])


class RetryOnRefusal(Wiring):
    def test_refused_writes_retry_once_then_say_so(self):
        import propose_wiring as pw
        started = []

        def start(clone, change, summary, msgs, pub2name, requester):
            started.append(change)
            return {"wt": "/wt2", "branch": "b2", "change": change, "proc": Proc(0),
                    "summary": summary}, ""
        builds = Builds()
        said = []
        try_p, tick, *_ = pw.setup(
            {"owner": "MWest2020", "repos": ["wordsworth"]}, {"odin": {"nsec": "n", "npub": "p"}},
            "odin", lambda cid, t, *a: said.append(t), {}, builds, lambda cid: [],
            lambda *a, **k: None, issues=type("I", (), {"create": lambda s, *a: (9, "u", ""),
                                                        "comment": lambda s, *a: ""})(),
            log=lambda *a, **k: None, start=start, check=lambda j: "the session wrote nothing",
            refused=lambda j: ["/wt/openspec/changes/add-x/a.md"])
        try_p("!propose wordsworth add-x Do x.", "odin", "general", "cid", [], "mark")
        tick()                                 # refused -> one retry
        self.assertEqual(started, ["add-x", "add-x"])
        tick()                                 # refused again -> said, no third start
        self.assertEqual(len(started), 2)
        self.assertIn("1 writes inside the fence were refused", said[-1])


if __name__ == "__main__":
    unittest.main()
