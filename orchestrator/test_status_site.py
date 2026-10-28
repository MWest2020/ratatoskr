import datetime
import json
import os
import subprocess
import tempfile
import unittest
from zoneinfo import ZoneInfo

import status_scrub
import status_site

NOW = datetime.datetime(2026, 10, 28, 12, 0, tzinfo=ZoneInfo("Europe/Amsterdam"))


class Scrub(unittest.TestCase):
    def test_a_secret_stops_everything(self):
        for s in ("key sk-ant-api03-abcdefghijkl", "tskey-api-kqeP94eRLy11CNTRL",
                  "ghp_" + "a" * 36, "cfat_" + "b" * 30, "password: hunter2"):
            with self.assertRaises(status_scrub.Leak):
                status_scrub.clean_tree({"projects": [{"title": s}]})

    def test_emails_and_ids_are_stripped(self):
        out = status_scrub.clean("mail mark@westerweel.work about 6e01a86a-4c86-4a2c-a526-0fe76c374d52")
        self.assertNotIn("@", out)
        self.assertNotIn("6e01a86a", out)

    def test_a_private_repo_is_named_not_linked(self):
        self.assertIsNone(status_scrub.public_url("https://github.com/x/y", False))
        self.assertEqual(status_scrub.public_url("https://github.com/x/y", True), "https://github.com/x/y")


def fake_gh(responses):
    def run(argv, **kw):
        if argv[0] == "journalctl":
            return subprocess.CompletedProcess(argv, 0, stdout="x [listener] build refused: budget\n", stderr="")
        key = " ".join(argv[1:3])
        for k, v in responses.items():
            if key.startswith(k) and (len(k.split()) < 3 or True):
                if callable(v):
                    v = v(argv)
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(v), stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="no")
    return run


def issues_for(argv):
    repo = argv[argv.index("--repo") + 1]
    if repo.endswith("/wordsworth"):
        return [{"number": 5, "title": "propose: a-change", "url": "https://github.com/MWest2020/wordsworth/issues/5",
                 "comments": []},
                {"number": 6, "title": "propose: broken", "url": "https://github.com/MWest2020/wordsworth/issues/6",
                 "comments": [{"body": "**architect: FAIL** (verdict failed)\n- [summary] gap in spec"}]}]
    if repo.endswith("/convergence"):
        return [{"number": 7, "title": "propose: secret-game", "url": "https://github.com/MWest2020/convergence/issues/7",
                 "comments": []}]
    return []


def visibility(argv):
    return {"visibility": "PRIVATE" if argv[3].endswith("/convergence") else "PUBLIC"}


class Build(unittest.TestCase):
    def setUp(self):
        self.run = fake_gh({"issue list": issues_for, "pr list": [], "repo view": visibility,
                            "search issues": [{"number": 196, "title": "Ranking questions", "url": "u",
                                               "body": "Question\nDefault: the report stays open",
                                               "repository": {"name": "wordsworth"}}]})
        self.state = {"queued": [{"repo": "wordsworth", "change": "a-change"}]}

    def data(self):
        return status_site.build(NOW, run=self.run, state=self.state)

    def test_stage_comes_from_the_build_state(self):
        ww = next(p for p in self.data()["projects"] if p["name"] == "wordsworth")
        self.assertEqual(ww["in_flight"][0]["stage"], "queued")

    def test_a_failed_verdict_is_stuck_with_its_role(self):
        stuck = self.data()["stuck"]
        self.assertTrue(any(s["change"] == "broken" and s["why"].startswith("architect FAIL") for s in stuck))

    def test_a_private_project_has_no_links(self):
        cv = next(p for p in self.data()["projects"] if p["name"] == "convergence")
        self.assertIsNone(cv["url"])
        self.assertIsNone(cv["in_flight"][0]["url"])

    def test_waiting_carries_the_default(self):
        self.assertEqual(self.data()["waiting"][0]["default"], "the report stays open")

    def test_generated_time_is_amsterdam(self):
        self.assertTrue(self.data()["generated"].endswith("+01:00"))


class Publish(unittest.TestCase):
    def test_unchanged_content_is_not_pushed_and_throttle_holds(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "data"))
            data = {"generated": "a", "projects": [], "stuck": [], "waiting": []}
            json.dump(data, open(os.path.join(t, "data", "status.json"), "w"))
            calls = []
            run = lambda argv, **kw: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", "")  # noqa: E731
            mark = os.path.join(t, "mark.json")
            self.assertEqual(status_site.publish({**data, "generated": "b"}, site=t, run=run, now=NOW, mark=mark),
                             "unchanged")
            json.dump({"pushed": NOW.timestamp() - 60}, open(mark, "w"))
            self.assertEqual(status_site.publish({**data, "waiting": [1]}, site=t, run=run, now=NOW, mark=mark),
                             "throttled")
            self.assertFalse(any("push" in a for a in calls))


if __name__ == "__main__":
    unittest.main()
