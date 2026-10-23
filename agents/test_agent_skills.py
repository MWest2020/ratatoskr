# SPDX-License-Identifier: MIT
"""Phase 5: an agent's declared skills are installed and invocable, and only
those (dontAsk refuses every Skill(...) not on the list)."""
import os
import tempfile
import unittest
from unittest import mock

import agent_skills
import agent_turn
import providers


def make_skill(src, slug):
    os.makedirs(os.path.join(src, slug, "iterations"))
    with open(os.path.join(src, slug, "SKILL.md"), "w") as fh:
        fh.write(f"---\nname: {slug}\n---\nbody\n")


class Install(unittest.TestCase):
    def test_only_declared_skills_and_missing_ones_are_said(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as root:
            make_skill(src, "read-state")
            make_skill(src, "not-declared")
            os.makedirs(os.path.join(root, ".claude", "skills", "old-one"))
            logs = []
            res = agent_skills.install({"odin": {"skills": ["read-state", "ghost"]},
                                        "architect": {"skills": []}}, root, source=src,
                                       log=lambda *a, **k: logs.append(a[0]))
            have = sorted(os.listdir(os.path.join(root, ".claude", "skills")))
            self.assertEqual(have, ["read-state"])           # not the undeclared, not stale
            self.assertFalse(os.path.exists(os.path.join(root, ".claude", "skills",
                                                         "read-state", "iterations")))
            self.assertEqual(res["read-state"], "")
            self.assertIn("no ghost/SKILL.md", res["ghost"])
            self.assertTrue(logs)

    def test_allow_rules_only_for_sane_slugs(self):
        self.assertEqual(agent_skills.allow_rules(["read-state", "../x", "A b"]),
                         ["Skill(read-state)"])


class Turn(unittest.TestCase):
    def test_the_turn_allows_its_own_skills(self):
        seen = {}

        def fake_run(provider, system, prompt, **k):
            seen.update(k)
            return {"answer": "ok", "error": ""}
        cfg = {"system": "You are odin.", "model": "sonnet", "allow": ["Read"], "deny": [],
               "routes": [], "nsec": "n", "npub": "p", "provider": "claude-p",
               "skills": ["read-state"], "channels": ["general"]}

        class Reg:
            cfg = {"types": {}}
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(providers, "run", fake_run), \
             mock.patch("reporting.report_run"), \
             mock.patch("reporting.progress_poster", return_value=None):
            os.makedirs(os.path.join(root, "knowledge"), exist_ok=True)
            turn = agent_turn.build_turn({"bouwer": cfg}, "odin", Reg(), lambda *a: True, {}, {},
                                         root, lambda *a, **k: None, log=lambda *a, **k: None)
            turn("bouwer", "general", "c", [{"pubkey": "p", "content": "x", "id": "m"}], 0,
                 "x", "mark", "m", "mention")
        self.assertEqual(seen["allow"], ["Read", "Skill(read-state)"])


if __name__ == "__main__":
    unittest.main()
