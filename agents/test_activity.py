# SPDX-License-Identifier: MIT
"""Which agent ran, on which model, with which skills and tools (Mark,
2026-10-24, for a LinkedIn post). Offline."""
import json
import os
import tempfile
import unittest

import activity
import build_runner


class Activity(unittest.TestCase):
    def test_tools_and_skills_from_a_stream(self):
        lines = [json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}),
                 json.dumps({"type": "assistant", "message": {"content": [
                     {"type": "tool_use", "name": "Read", "input": {}},
                     {"type": "tool_use", "name": "Skill", "input": {"skill": "read-state"}},
                     {"type": "tool_use", "name": "Read", "input": {}}]}}), "not json"]
        tools, skills = activity.tools_from_stream(lines)
        self.assertEqual(tools, {"Read": 2, "Skill": 1})
        self.assertEqual(skills, ["read-state"])
        self.assertEqual(activity.model_from_stream(lines), "claude-sonnet-5-5")

    def test_a_record_is_one_line(self):
        with tempfile.TemporaryDirectory() as t:
            log = os.path.join(t, "a.jsonl")
            activity.record("chat", "odin", "convergence", model="m", skills=["read-state"],
                            tools={"Read": 1}, cost=0.1, billing="api", log=log, ts=5)
            row = json.loads(open(log).read())
        self.assertEqual((row["agent"], row["billing"], row["tools"]), ("odin", "api", {"Read": 1}))

    def test_a_habitat_role_carries_its_model(self):
        lines = ["=== keten: rol builder ===", "[habitat] model uit rolbestand: sonnet",
                 "keten: builder -> habitat/builder/x"]
        (kind, role, detail), = build_runner.events(lines)
        self.assertEqual((kind, role, detail["model"]), ("passed", "builder", "sonnet"))


class Report(unittest.TestCase):
    def test_the_summary_counts_agents_models_and_tools(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "activity_report", os.path.join(os.path.dirname(__file__), "..", "scripts",
                                            "activity_report.py"))
        rep = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rep)
        rows = [{"ts": 1, "kind": "chat", "agent": "odin", "project": "general",
                 "model": "claude-sonnet-5-5", "tools": {"Read": 2}, "skills_used": ["read-state"],
                 "cost": 0.5, "turns": 3, "billing": "subscription"},
                {"ts": 2, "kind": "habitat", "agent": "builder", "project": "convergence",
                 "model": "sonnet", "tools": {}, "cost": 2.0, "turns": 40, "billing": "api"}]
        s = rep.summary(rows)
        self.assertEqual((s["runs"], s["cost"], s["models"]), (2, 2.5, {"Sonnet": 2}))
        self.assertEqual(s["agents"]["odin"]["tools"], {"Read": 2})
        self.assertEqual(s["billing_cost"], {"subscription": 0.5, "api": 2.0})


class OffInTests(unittest.TestCase):
    def test_the_real_log_is_not_written_until_enabled(self):
        before = os.path.getsize(activity.LOG) if os.path.exists(activity.LOG) else 0
        activity.record("chat", "test-agent", "x")
        after = os.path.getsize(activity.LOG) if os.path.exists(activity.LOG) else 0
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
