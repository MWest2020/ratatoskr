# SPDX-License-Identifier: MIT
"""Only the projects we are busy with, each kept short (Mark, 2026-11-28).

status_activity scores and ranks; status_roadmap picks at most three open
items; status_digest carries the same order to the daily mail. The seam (one
collect() run feeding both the page and the digest) is tested through
status_site with the fake GitHub of status_fakes.
"""
import unittest
from unittest import mock

import status_activity as sa
import status_digest
import status_roadmap
import status_site
from status_fakes import NOW, fake_gh, responses


def pr(repo, n, when, title="t", key="closedAt"):
    return {"repository": {"name": repo}, "number": n, "title": title, key: when}


class Settings(unittest.TestCase):
    def test_defaults_are_five_projects_and_seven_days(self):
        self.assertEqual(sa.settings({}), (5, 7))

    def test_both_come_from_the_environment(self):
        self.assertEqual(sa.settings({"STATUS_TOP": "3", "STATUS_WINDOW_DAYS": "14"}), (3, 14))

    def test_a_bad_value_says_which(self):
        for env in ({"STATUS_TOP": "five"}, {"STATUS_TOP": "0"}, {"STATUS_WINDOW_DAYS": "-1"}):
            with self.assertRaisesRegex(ValueError, "STATUS_TOP"):
                sa.settings(env)


class Score(unittest.TestCase):
    def activity(self, days=7, state=None, **searches):
        calls = []
        run = fake_gh(responses(**searches))
        counting = lambda argv, **kw: calls.append(argv) or run(argv, **kw)  # noqa: E731
        return sa.Activity("MWest2020", status_site.gh, counting, NOW, days, state), calls

    def test_merged_prs_commits_and_closed_issues_in_the_window_count(self):
        act, _ = self.activity(closed=[pr("wordsworth", 7, "2026-10-25T08:00:00Z")])
        ww = act.of("wordsworth")
        self.assertEqual(ww["score"], 2)  # PR 40 and issue 7; PR 30 is older than a week
        self.assertEqual(ww["recent"], {"kind": "merged", "title": "pilot: the report", "date": "2026-10-27"})
        cv = act.of("convergence")
        self.assertEqual((cv["score"], cv["recent"]["kind"]), (1, "commit"))

    def test_a_wider_window_counts_the_older_pr(self):
        self.assertEqual(self.activity(days=10)[0].of("wordsworth")["score"], 2)

    def test_an_open_pr_touched_this_week_and_a_running_build_count_once_each(self):
        prs = [pr("habitat", 3, "2026-10-27T08:00:00Z", key="updatedAt"),
               pr("habitat", 4, "2026-10-26T08:00:00Z", key="updatedAt"),
               pr("handbook", 5, "2026-10-01T08:00:00Z", key="updatedAt")]
        act, _ = self.activity(open_prs=prs, state={"running": [{"repo": "habitat", "change": "x"}]})
        self.assertEqual(act.of("habitat")["score"], 2)
        self.assertEqual(act.of("handbook"), {"score": 0, "last": "2026-10-01", "recent": None})

    def test_the_owner_wide_searches_run_once_per_run(self):
        act, calls = self.activity()
        for repo in ("wordsworth", "convergence", "habitat"):
            act.of(repo)
        searches = [c for c in calls if c[1] == "search"]
        self.assertEqual(len(searches), 3)

    def test_a_failing_search_stops_the_run_rather_than_emptying_the_page(self):
        act = sa.Activity("MWest2020", lambda argv, run: None, None, NOW, 7, {})
        with self.assertRaisesRegex(sa.Unavailable, "failed twice"):
            act.of("wordsworth")


def project(name, score, last):
    return {"name": name, "activity": {"score": score, "last": last}}


class Rank(unittest.TestCase):
    def test_top_n_by_score_then_newest(self):
        ps = [project("a", 1, "2026-10-20"), project("b", 9, "2026-10-27"), project("c", 1, "2026-10-27"),
              project("d", 4, "2026-10-26")]
        shown, inactive = sa.rank(ps, 3)
        self.assertEqual([p["name"] for p in shown], ["b", "d", "c"])
        self.assertEqual(inactive, [{"name": "a", "last": "2026-10-20"}])

    def test_no_activity_drops_out_even_with_room_left(self):
        shown, inactive = sa.rank([project("a", 2, "2026-10-27"), project("z", 0, "2026-09-01"),
                                   project("y", 0, None)], 5)
        self.assertEqual([p["name"] for p in shown], ["a"])
        self.assertEqual(inactive, [{"name": "z", "last": "2026-09-01"}, {"name": "y", "last": None}])


def item(text, evidence, status="open"):
    return {"item": text, "status": status, "evidence": evidence}


class Gap(unittest.TestCase):
    ITEMS = [item("first", "https://github.com/MWest2020/w/issues/54"),
             item("done", "https://github.com/MWest2020/w/pull/1", "done"),
             item("second", "https://github.com/MWest2020/w/blob/main/docs/x.md"),
             item("third", "https://github.com/MWest2020/w/issues/541"),
             item("fourth", "https://github.com/MWest2020/w/tree/main/openspec/changes/key-service-delete")]

    def test_refs_are_exact(self):
        self.assertEqual(status_roadmap.refs(self.ITEMS[3]["evidence"]), {"w#541"})
        self.assertEqual(status_roadmap.refs("https://x/openspec/changes/archive/2026-11-01-a/tasks.md"), set())

    def test_at_most_three_oldest_first_and_the_rest_counted(self):
        shown, more = status_roadmap.gap(self.ITEMS, True)
        self.assertEqual([g["item"] for g in shown], ["first", "second", "third"])
        self.assertEqual(more, 1)

    def test_in_progress_comes_first(self):
        shown, _ = status_roadmap.gap(self.ITEMS, False, {"w#541", "change:key-service-delete"})
        self.assertEqual([(g["item"], g["doing"]) for g in shown], [("third", True), ("fourth", True),
                                                                    ("first", False)])
        self.assertTrue(all(g["url"] is None for g in shown))


class Collect(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(status_digest, "SITE_STATE", "/nonexistent/site-freshness.json")
        p.start()
        self.addCleanup(p.stop)

    def collect(self, env=None, **searches):
        return status_site.collect(NOW, run=fake_gh(responses(**searches)), state={}, env=env or {})

    def test_the_page_shows_the_busiest_and_names_the_rest(self):
        page, digest = self.collect({"STATUS_TOP": "1"})
        self.assertEqual([p["name"] for p in page["projects"]], ["wordsworth"])
        self.assertEqual(page["inactive"], [{"name": "convergence", "last": "2026-10-26"}])
        self.assertEqual(page["window_days"], 7)
        ww = page["projects"][0]
        self.assertEqual((ww["gap_more"], ww["recent"]["title"]), (0, "pilot: the report"))
        self.assertTrue(ww["roadmap_url"].endswith("/wordsworth/blob/main/docs/reference/roadmap.yml"))
        self.assertEqual([a["repo"] for a in digest["projects_active"]], ["wordsworth"])
        self.assertIn("Pilot (1/2 done)", digest["projects_active"][0]["status"])

    def test_a_quiet_week_leaves_nothing_on_the_page_but_every_question_in_the_digest(self):
        page, digest = self.collect(merged=[])
        self.assertEqual([p["name"] for p in page["projects"]], ["convergence"])
        self.assertEqual([w["repo"] for w in digest["waiting"]], ["convergence", "wordsworth"])

    def test_questions_follow_the_activity_order(self):
        waiting = [w["repo"] for w in self.collect()[1]["waiting"]]
        self.assertEqual(waiting, ["wordsworth", "convergence"])


if __name__ == "__main__":
    unittest.main()
