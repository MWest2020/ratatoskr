# SPDX-License-Identifier: MIT
"""Odin's factory markers and Mark's `!yes` (odin-runs-the-factory, phase 4).
Closing is the part that must never happen by itself, so most cases are about
who may close what, and when. The factory, the relay and git are faked."""
import json
import os
import tempfile
import unittest

import factory_wiring as fw


class FakeOps:
    class StepError(Exception):
        pass

    def __init__(self):
        self.calls = []

    def channel_record(self, *a):
        self.calls.append(("record",) + a)

    def channel_close(self, name, cid, nsec, today):
        self.calls.append(("close-channel", name, cid))

    def role_retire(self, name, today):
        self.calls.append(("retire", name))

    def redeploy_listener(self):
        self.calls.append(("redeploy",))


class Proc:
    def __init__(self, code=0):
        self.code = code

    def poll(self):
        return self.code


SPEC = "!role\nA new one.\n```yaml\nname: scout\nmodel: haiku\n```\n"


class Wiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.said, self.ops, self.clock, self.served = [], FakeOps(), [1000.0], []
        self.result = {"ok": True, "name": "scout", "done": ["handbook u"]}

        def popen(argv, stdout, **kw):
            with open(stdout.name, "w") as fh:
                fh.write(json.dumps(self.result) + "\n")
            self.argv = argv
            return Proc(0)
        agents = {"odin": {"nsec": "n", "npub": "p"}, "architect": {}, "bouwer": {}}
        self.marker, self.yes, self.tick = fw.setup(
            agents, "odin", "mark", lambda cid, t, *a: self.said.append(t),
            {"general": "cid-g", "werkplaats": "cid-w"}, self.tmp.name, "base",
            popen=popen, ops=self.ops, now=lambda: self.clock[0], log=lambda *a, **k: None,
            fetch_def=lambda base, name: self.served.pop(0) if self.served else None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_role_runs_the_factory_and_restarts_only_once_served(self):
        self.marker(SPEC, "odin", "general", "c")
        self.assertTrue(self.argv[-2:][0] == "--spec" and self.argv[-1].endswith(".yml"))
        with open(self.argv[-1]) as fh:
            self.assertIn("name: scout", fh.read())
        self.tick()                                        # factory finished
        self.assertIn("role **scout** made", self.said[-1])
        self.assertNotIn(("redeploy",), self.ops.calls)    # not served yet
        self.served = [{"x": 1}, {"x": 1}, {"x": 1}]
        for _ in range(3):
            self.clock[0] += 31
            self.tick()
        self.assertIn(("redeploy",), self.ops.calls)

    def test_only_the_first_line_of_the_hubs_answer(self):
        self.marker("quoting:\n" + SPEC, "odin", "general", "c")
        self.marker(SPEC, "architect", "general", "c")
        self.assertFalse(hasattr(self, "argv"))

    def test_a_failed_role_says_why(self):
        self.result = {"ok": False, "errors": ["role 'bouwer' exists or is reserved"]}
        self.marker(SPEC, "odin", "general", "c")
        self.tick()
        self.assertIn("role not created: role 'bouwer' exists", self.said[-1])

    def test_close_only_proposes(self):
        self.marker("!close channel werkplaats", "odin", "general", "c")
        self.assertEqual(self.ops.calls, [])
        self.assertIn("answer `!yes`", self.said[-1])

    def test_marks_yes_closes_and_nobody_elses_does(self):
        self.marker("!close channel werkplaats", "odin", "general", "c")
        self.yes("!yes", "architect", "c")
        self.assertEqual(self.ops.calls, [])
        self.yes("!yes", "mark", "c")
        self.assertEqual(self.ops.calls[0], ("close-channel", "werkplaats", "cid-w"))
        self.yes("!yes", "mark", "c")                      # nothing left to confirm
        self.assertIn("nothing waits", self.said[-1])

    def test_a_proposal_expires_and_stays_in_its_channel(self):
        self.marker("!close role bouwer", "odin", "general", "c")
        self.yes("!yes", "mark", "other-channel")
        self.clock[0] += fw.PROPOSAL_TTL + 1
        self.yes("!yes", "mark", "c")
        self.assertEqual([c for c in self.ops.calls if c[0] == "retire"], [])

    def test_the_hub_cannot_be_proposed_for_closing(self):
        self.marker("!close role odin", "odin", "general", "c")
        self.assertIn("cannot propose", self.said[-1])

    def test_only_the_hub_is_told(self):
        self.assertEqual(fw.clause("architect", "odin"), "")
        self.assertIn("!role", fw.clause("odin", "odin"))


if __name__ == "__main__":
    unittest.main()
