# SPDX-License-Identifier: MIT
"""The factory's pure part: what a role spec may be, and that the definition it
renders is one the listener and the handbook gate accept as written."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
import defparse  # noqa: E402

import factory_def as fd  # noqa: E402

REG = {"read-state": ["Bash(python3 agents/readshell.py:*)"], "no-ai-slop": []}
SPEC = {"name": "scout", "model": "sonnet", "channels": ["werkplaats"],
        "skills": ["read-state"], "mandate": "Finds out what is open.",
        "contract": {"takes": "a status question", "produces": "a short answer",
                     "done_when": "Mark has the state", "hands_off_to": "nobody",
                     "not_mine": "building (bouwer)"},
        "prompt": "You are 'scout'.\nShort and factual."}


class Validate(unittest.TestCase):
    def errs(self, **change):
        return fd.validate({**SPEC, **change}, REG, {"werkplaats", "general"}, {"odin", "bouwer"})

    def test_a_good_spec(self):
        self.assertEqual(self.errs(), [])

    def test_an_existing_or_reserved_role_is_refused(self):
        for n in ("bouwer", "odin", "mark"):
            self.assertTrue(any("Mark's" in e for e in self.errs(name=n)), n)

    def test_the_rest(self):
        self.assertTrue(self.errs(name="Scout!"))
        self.assertTrue(self.errs(model="gpt"))
        self.assertTrue(self.errs(channels=["nowhere"]))
        self.assertTrue(self.errs(skills=["unknown-skill"]))
        self.assertTrue(self.errs(contract={"takes": "x"}))
        self.assertTrue(self.errs(prompt=""))


class Render(unittest.TestCase):
    def test_tools_follow_from_skills(self):
        self.assertEqual(fd.tools_for(["read-state", "no-ai-slop"], REG),
                         ["Read", "Grep", "Glob", "Bash(python3 agents/readshell.py:*)"])
        self.assertEqual(fd.tools_for([], REG), ["Read", "Grep", "Glob"])

    def test_the_listener_reads_what_the_factory_writes(self):
        d = defparse.parse_def(fd.render(SPEC, "npub1x", REG, "2026-10-22"))
        self.assertEqual(d["model"], "sonnet")
        self.assertEqual(d["channels"], ["werkplaats"])
        self.assertEqual(d["allow"], ["Read", "Grep", "Glob", "Bash(python3 agents/readshell.py:*)"])
        self.assertEqual(d["deny"], ["Write", "Edit"])
        self.assertEqual(d["skills"], ["read-state"])
        self.assertTrue(d["system"].startswith("You are 'scout'."))
        self.assertIn("**Not mine:** building (bouwer)", d["contract"])

    def test_no_bash_skill_means_bash_denied(self):
        d = defparse.parse_def(fd.render({**SPEC, "skills": []}, "npub1x", REG, "2026-10-22"))
        self.assertEqual(d["deny"], ["Write", "Edit", "Bash"])



class Lists(unittest.TestCase):
    def test_list_fields_render_as_sub_bullets(self):
        spec = {**SPEC, "contract": {**SPEC["contract"], "not_mine": ["building", "verdicts"]}}
        d = defparse.parse_def(fd.render(spec, "npub1x", REG, "2026-10-23"))
        self.assertIn("- **Not mine:**\n  - building\n  - verdicts", d["contract"])
        self.assertNotIn("['", d["contract"])


class RoomMembers(unittest.TestCase):
    YML = ("channels:\n  general:\n    id: g\n  werkplaats:\n    id: w\n    room:\n"
           "      members: [architect, bouwer, reviewer]\n      repos: [ratatoskr]\n")

    def test_a_role_in_a_room_joins_its_triage(self):
        import factory_ops
        out = factory_ops.with_room_member(self.YML, "pilotleider", ["werkplaats"])
        self.assertIn("members: [architect, bouwer, reviewer, pilotleider]", out)
        self.assertEqual(factory_ops.with_room_member(out, "pilotleider", ["werkplaats"]), out)

    def test_a_channel_that_is_no_room_is_left_alone(self):
        import factory_ops
        self.assertEqual(factory_ops.with_room_member(self.YML, "x", ["general"]), self.YML)


if __name__ == "__main__":
    unittest.main()
