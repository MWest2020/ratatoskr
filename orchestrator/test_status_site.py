import datetime
import json
import os
import subprocess
import tempfile
import unittest
from zoneinfo import ZoneInfo

import base64

import status_digest
import status_roadmap
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
                 "comments": [{"body": "**architect: FAIL** (verdict failed)\n- [summary] gap in spec",
                               "createdAt": "2026-10-27T08:00:00Z"}]}]
    if repo.endswith("/convergence"):
        return [{"number": 7, "title": "propose: secret-game", "url": "https://github.com/MWest2020/convergence/issues/7",
                 "comments": []}]
    return []


ROADMAP = """# draft
project: wordsworth
goal: "A privacy-safe corpus"
current: pilot
phases:
  - {id: poc, name: PoC, summary: built}
  - {id: pilot, name: Pilot, summary: one dossier}
  - {id: production, name: Production, summary: later}
done_means:
  - {item: Report filled, status: done, evidence: "https://github.com/MWest2020/wordsworth/pull/284"}
  - {item: Every PDF redacted, status: open, evidence: "https://github.com/MWest2020/wordsworth/issues/259"}
"""


def roadmap_for(argv):
    if "/wordsworth/" in argv[2]:
        return {"content": base64.b64encode(ROADMAP.encode()).decode()}
    if "/convergence/" in argv[2]:
        return {"content": base64.b64encode(ROADMAP.replace("wordsworth", "convergence").encode()).decode()}
    return None


def visibility(argv):
    return {"visibility": "PRIVATE" if argv[3].endswith("/convergence") else "PUBLIC"}


class Build(unittest.TestCase):
    def setUp(self):
        self.run = fake_gh({"issue list": issues_for, "repo view": visibility, "api": roadmap_for,
                            "search issues": [{"number": 196, "title": "Ranking questions", "url": "u",
                                               "body": "Question\nDefault: the report stays open",
                                               "repository": {"name": "wordsworth"},
                                               "createdAt": "2026-10-20T08:00:00Z"},
                                              {"number": 95, "title": "Legal sign-off", "url": "https://github.com/MWest2020/convergence/issues/95",
                                               "body": "Default: devnet only", "repository": {"name": "convergence"},
                                               "createdAt": "2026-10-28T08:00:00Z"}]})
        self.state = {"queued": [{"repo": "wordsworth", "change": "a-change"}]}

    def collect(self):
        return status_site.collect(NOW, run=self.run, state=self.state)

    def test_the_page_has_no_questions_and_nothing_stuck(self):
        page = self.collect()[0]
        self.assertNotIn("waiting", page)
        self.assertNotIn("stuck", page)

    def test_a_project_row_has_phase_progress_and_gap(self):
        ww = next(p for p in self.collect()[0]["projects"] if p["name"] == "wordsworth")
        self.assertEqual(ww["phase"], "Pilot")
        self.assertEqual(ww["progress"], {"done": 1, "total": 2})
        self.assertEqual([g["item"] for g in ww["gap"]], ["Every PDF redacted"])
        self.assertEqual([p["state"] for p in ww["phases"]], ["past", "current", "next"])
        self.assertEqual(ww["in_flight"][0]["stage"], "queued")

    def test_a_private_project_has_no_links(self):
        cv = next(p for p in self.collect()[0]["projects"] if p["name"] == "convergence")
        self.assertIsNone(cv["url"])
        self.assertTrue(all(g["url"] is None for g in cv["gap"]))

    def test_the_digest_carries_questions_with_their_default(self):
        w = self.collect()[1]["waiting"]
        self.assertEqual(w[0]["default"], "the report stays open")
        self.assertEqual(next(x for x in w if x["repo"] == "convergence")["default"], "devnet only")

    def test_impediments_old_fail_refusal_and_long_wait(self):
        kinds = sorted(i["kind"] for i in self.collect()[1]["impediments"])
        # broken failed 2026-10-27 08:00 (>12h before NOW), a refusal in the journal,
        # #196 open since 2026-10-20 (>3 days); #95 is only a day old
        self.assertEqual(kinds, ["build-failed", "refused", "waiting-too-long"])

    def test_generated_time_is_amsterdam(self):
        g = self.collect()[0]["generated"]
        self.assertTrue(g.endswith("+01:00"))
        self.assertEqual(len(g), 25)


class Roadmap(unittest.TestCase):
    def test_a_current_phase_that_does_not_exist_is_refused(self):
        with self.assertRaises(status_roadmap.BadRoadmap):
            status_roadmap.parse(ROADMAP.replace("current: pilot", "current: nope"))

    def test_an_item_without_evidence_is_refused(self):
        with self.assertRaises(status_roadmap.BadRoadmap):
            status_roadmap.parse(ROADMAP.replace('"https://github.com/MWest2020/wordsworth/pull/284"', "later"))

    def test_the_real_roadmaps_parse(self):
        here = os.path.dirname(os.path.abspath(__file__))
        doc = status_roadmap.parse(open(os.path.join(here, "..", "docs", "reference", "roadmap.yml")).read())
        self.assertEqual(doc["project"], "ratatoskr")


class Digest(unittest.TestCase):
    def test_it_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "x", "mark-digest.json")
            status_digest.write({"generated": "g", "waiting": [], "impediments": []}, path)
            self.assertEqual(json.load(open(path))["generated"], "g")
            self.assertFalse(os.path.exists(path + ".tmp"))


class Publish(unittest.TestCase):
    def test_unchanged_content_is_not_pushed_and_throttle_holds(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "data"))
            data = {"generated": "a", "projects": []}
            json.dump(data, open(os.path.join(t, "data", "status.json"), "w"))
            calls = []
            run = lambda argv, **kw: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", "")  # noqa: E731
            mark = os.path.join(t, "mark.json")
            self.assertEqual(status_site.publish({**data, "generated": "b"}, site=t, run=run, now=NOW, mark=mark),
                             "unchanged")
            json.dump({"pushed": NOW.timestamp() - 60}, open(mark, "w"))
            self.assertEqual(status_site.publish({**data, "projects": [1]}, site=t, run=run, now=NOW, mark=mark),
                             "throttled")
            self.assertFalse(any("push" in a for a in calls))


if __name__ == "__main__":
    unittest.main()
