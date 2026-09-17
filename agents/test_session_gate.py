# SPDX-License-Identifier: MIT
"""Offline tests for the GATE of a work session: marker, authorisation, clause.

The runner (register, harvest, limits, report) lives in test_sessions.py. That
split follows the code: session_gate.py is pure, sessions.py touches processes.

Run with: cd agents && python3 -m unittest test_session_gate
"""
import os
import tempfile
import unittest

import prompts
import session_gate


CFG = {
    "max_concurrent": 2,
    "types": {
        "zettelkast": {"workdir": "/tmp", "starters": ["odin", "mark"],
                       "identity": "odin", "tools": ["Read"], "max_seconds": 60,
                       "prompt": "Opdracht: {task}"},
    },
}


class Marker(unittest.TestCase):
    def test_reads_type_and_task(self):
        self.assertEqual(session_gate.read_marker("hoi\n!sessie zettelkast kijk naar de clips"),
                         ("zettelkast", "kijk naar de clips"))

    def test_without_task(self):
        self.assertEqual(session_gate.read_marker("!sessie zettelkast"), ("zettelkast", ""))

    def test_only_the_first_counts(self):
        """One message sets at most one session in motion."""
        t = "!sessie zettelkast een\n!sessie zettelkast twee"
        self.assertEqual(session_gate.read_marker(t)[1], "een")

    def test_no_marker(self):
        self.assertIsNone(session_gate.read_marker("praat over !sessie in een zin"))

    def test_stripping_removes_the_line(self):
        """A posted marker must not be readable again."""
        out = session_gate.strip_marker("voor\n!sessie zettelkast doe iets\nna")
        self.assertNotIn("!sessie", out)
        self.assertIn("voor", out)
        self.assertIn("na", out)

    def test_stripping_leaves_the_second_but_starts_nothing(self):
        out = session_gate.strip_marker("!sessie zettelkast een\n!sessie zettelkast twee")
        self.assertEqual(session_gate.read_marker(out), ("zettelkast", "twee"))

class Authorisation(unittest.TestCase):
    def may(self, type_name="zettelkast", starter="odin", requester="mark", running=()):
        return session_gate.may_start(CFG, type_name, starter, requester, list(running))

    def test_unknown_type_names_what_does_exist(self):
        ok, reason = self.may(type_name="nietbestaand")
        self.assertFalse(ok)
        self.assertIn("zettelkast", reason)

    def test_unauthorised_starter(self):
        ok, reason = self.may(starter="roodteam")
        self.assertFalse(ok)
        self.assertIn("roodteam", reason)

    def test_agent_on_behalf_of_someone_not_allowed(self):
        """Odin may start, but not for someone who is not a starter themselves."""
        ok, reason = self.may(requester="roodteam")
        self.assertFalse(ok)
        self.assertIn("namens", reason)

    def test_unknown_sender_is_refused(self):
        """PUB2NAME gives '?' for an unknown pubkey — never a listed starter."""
        self.assertFalse(self.may(starter="?", requester="?")[0])

    def test_one_session_per_requester(self):
        """The limit is per requester: two people through odin is fine."""
        ok, reason = self.may(running=[{"requester": "mark"}])
        self.assertFalse(ok)
        self.assertIn("al een sessie", reason)

    def test_second_person_via_the_same_agent_is_allowed(self):
        ok, reason = self.may(requester="odin", running=[{"requester": "mark"}])
        self.assertTrue(ok, reason)

    def test_global_upper_bound(self):
        running = [{"requester": "x"}, {"requester": "y"}]
        ok, reason = self.may(running=running)
        self.assertFalse(ok)
        self.assertIn("maximaal", reason)

    def test_allowed(self):
        self.assertEqual(self.may(), (True, ""))

class Clause(unittest.TestCase):
    """An agent that is no starter should not read that it can start sessions."""

    def test_starter_gets_the_types(self):
        t = prompts.session_clause(CFG, "odin")
        self.assertIn("!sessie", t)
        self.assertIn("zettelkast", t)

    def test_non_starter_gets_nothing(self):
        self.assertEqual(prompts.session_clause(CFG, "roodteam"), "")

    def test_no_types_no_clause(self):
        self.assertEqual(prompts.session_clause({"types": {}}, "odin"), "")

class OneListener(unittest.TestCase):
    """Two listeners = every message answered twice and every session started
    twice. Measured 2026-09-11 in #architectuur: one marker, two sessions."""

    def test_second_instance_gets_nothing(self):
        import bootstrap
        path = os.path.join(tempfile.mkdtemp(), "lock")
        first = bootstrap.only_me(path)
        self.assertIsNotNone(first)
        self.assertIsNone(bootstrap.only_me(path))
        first.close()                       # lock released
        second = bootstrap.only_me(path)
        self.assertIsNotNone(second)
        second.close()


if __name__ == "__main__":
    unittest.main()
