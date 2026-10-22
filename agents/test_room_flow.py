# SPDX-License-Identifier: MIT
"""The shared room end to end, with GitHub, triage and the model faked: which
issue a message lands on, who answers, what the room shows, and how hand-offs
are bounded. The fakes record every call, so "it is on the issue" is checked."""
import unittest

import room_flow
import rooms

ROOM = {"members": ["architect", "bouwer", "reviewer"], "repos": ["ratatoskr", "handbook"],
        "max_hops": 3}
CONTRACTS = {
    "architect": "- **Takes:** design questions.\n- **Hands off to:** bouwer, with the decision.",
    "bouwer": "- **Takes:** a decided design.\n- **Hands off to:** reviewer, with the branch.",
    "reviewer": "- **Takes:** a branch.\n- **Hands off to:** on go, Mark.",
}
AGENTS = {h: {"contract": c} for h, c in CONTRACTS.items()}
PUB2NAME = {"pa": "architect", "pb": "bouwer", "pr": "reviewer", "pm": "mark"}


class FakeIssues:
    def __init__(self, fail_create=False):
        self.calls, self.fail_create, self.next = [], fail_create, 41

    def labels(self, room, handle):
        return ["agent-work", f"room:{room}", f"agent:{handle}"]

    def url(self, repo, n):
        return f"https://github.com/MWest2020/{repo}/issues/{n}"

    def create(self, repo, title, body, labels):
        self.calls.append(("create", repo, title, labels))
        if self.fail_create:
            return 0, "", "HTTP 503"
        self.next += 1
        return self.next, self.url(repo, self.next), ""

    def comment(self, repo, n, body):
        self.calls.append(("comment", repo, n, body))
        return ""

    def relabel(self, repo, n, old, new):
        self.calls.append(("relabel", repo, n, old, new))
        return ""

    def close(self, repo, n, body):
        self.calls.append(("close", repo, n, body))
        return ""


class Room:
    def __init__(self, answers, triage=None, fail_create=False):
        self.said, self.turns, self.answers = [], [], dict(answers)
        self.issues = FakeIssues(fail_create)
        tri = triage or (lambda c, r, a: ({"owners": ["architect"], "repo": "ratatoskr",
                                           "title": "a design question",
                                           "reason": "Takes: design questions"}, ""))

        def send(cid, text, nsec, npub):
            self.said.append(text)
            return True

        def run_turn(handle, cname, cid, msgs, i, content, writer, mid, reason,
                     extra="", suffix="", clean=None):
            self.turns.append((handle, reason, extra, content))
            ans = self.answers.get(handle, f"{handle} answers")
            return ans, clean(ans) if clean else ans

        self.handle = room_flow.build({"werkplaats": ROOM}, AGENTS, send, run_turn,
                                      ("nsec", "npub"), PUB2NAME, issues=self.issues,
                                      triage_run=tri)

    def say(self, content, earlier=(), mentioned=()):
        msgs = list(earlier) + [{"pubkey": "pm", "content": content}]
        self.handle("werkplaats", "cid", msgs, len(msgs) - 1, content, "mark", "m1",
                    lambda h: h in mentioned)


class NewWork(unittest.TestCase):
    def test_triage_opens_an_issue_and_the_owner_answers_on_it(self):
        r = Room({})
        r.say("how should the room pick an owner?")
        self.assertEqual(r.issues.calls[0][0:2], ("create", "ratatoskr"))
        self.assertIn("agent:architect", r.issues.calls[0][3])
        self.assertTrue(r.said[0].startswith("→ architect takes this (triage"))
        self.assertIn("· ratatoskr#42", r.said[0])
        self.assertEqual(r.turns[0][0:2], ("architect", "triage"))
        self.assertIn("ratatoskr#42", r.turns[0][2])
        self.assertIn(("comment", "ratatoskr", 42, "**architect**:\n\narchitect answers"),
                      r.issues.calls)

    def test_no_issue_means_no_turn(self):
        r = Room({}, fail_create=True)
        r.say("build it")
        self.assertEqual(r.turns, [])
        self.assertIn("not started: could not open an issue on ratatoskr: HTTP 503", r.said[0])

    def test_a_failed_triage_is_said_not_swallowed(self):
        r = Room({}, triage=lambda c, ro, a: (None, "nobody's contract covers this: lunch"))
        r.say("what's for lunch?")
        self.assertEqual(r.turns, [])
        self.assertEqual(r.issues.calls, [])
        self.assertIn("nobody took this", r.said[0])


class Continuing(unittest.TestCase):
    EARLIER = [{"pubkey": "pm", "content": "start"},
               {"pubkey": "pb", "content": "here is the plan\n\n· ratatoskr#7"}]

    def test_a_follow_up_continues_the_issue_without_triage(self):
        def no_triage(*a):
            raise AssertionError("triage must not run on a follow-up")
        r = Room({}, triage=no_triage)
        r.say("and the tests?", earlier=self.EARLIER)
        self.assertEqual(r.turns[0][0:2], ("bouwer", "vervolg"))
        self.assertEqual(r.issues.calls[0][0:3], ("comment", "ratatoskr", 7))
        self.assertEqual(r.said, [])  # no claim line for a follow-up

    def test_a_mention_takes_over_the_current_issue(self):
        r = Room({})
        r.say("@reviewer have a look", earlier=self.EARLIER, mentioned=("reviewer",))
        self.assertEqual(r.turns[0][0:2], ("reviewer", "mention"))
        self.assertIn("· ratatoskr#7", r.said[0])
        self.assertNotIn("create", [c[0] for c in r.issues.calls])


class HandOff(unittest.TestCase):
    def test_an_allowed_hand_off_moves_the_issue_and_runs_the_next_agent(self):
        r = Room({"architect": "decided: one triage call\n!handoff bouwer write the change",
                  "bouwer": "change written\n!done change on branch room-x"})
        r.say("design the room")
        self.assertEqual([t[0] for t in r.turns], ["architect", "bouwer"])
        self.assertIn(("relabel", "ratatoskr", 42, "agent:architect", "agent:bouwer"),
                      r.issues.calls)
        self.assertIn("↪ architect → bouwer: write the change\n\n· ratatoskr#42", r.said)
        self.assertIn("write the change", r.turns[1][3])
        self.assertEqual(r.issues.calls[-1][0], "close")
        self.assertTrue(r.said[-1].startswith("✓ bouwer: change on branch room-x"))
        # the markers are not what the room or the issue shows
        self.assertIn(("comment", "ratatoskr", 42, "**architect**:\n\ndecided: one triage call"),
                      r.issues.calls)

    def test_a_hand_off_outside_the_contract_is_refused(self):
        r = Room({"architect": "done thinking\n!handoff reviewer review my idea"})
        r.say("design the room")
        self.assertEqual([t[0] for t in r.turns], ["architect"])
        self.assertIn("does not name that agent", r.said[-1])

    def test_the_hop_limit_holds(self):
        loop = {"architect": "!handoff bouwer go", "bouwer": "!handoff reviewer go",
                "reviewer": "!handoff architect go"}
        contracts = dict(CONTRACTS, reviewer="- **Hands off to:** architect")
        AGENTS["reviewer"]["contract"] = contracts["reviewer"]
        try:
            r = Room(loop)
            r.say("design the room")
        finally:
            AGENTS["reviewer"]["contract"] = CONTRACTS["reviewer"]
        self.assertEqual(len(r.turns), ROOM["max_hops"] + 1)
        self.assertIn("hand-off limit (3) reached", r.said[-1])


class Pure(unittest.TestCase):
    def test_refs_only_count_for_the_rooms_repos(self):
        self.assertEqual(rooms.find_ref("see wordsworth#3 and ratatoskr#9", ["ratatoskr"]),
                         ("ratatoskr", 9))
        self.assertIsNone(rooms.find_ref("see wordsworth#3", ["ratatoskr"]))

    def test_handoff_targets_come_from_the_contract(self):
        self.assertEqual(rooms.handoff_targets(CONTRACTS["architect"], ROOM["members"],
                                               "architect"), ["bouwer"])
        self.assertEqual(rooms.handoff_targets(CONTRACTS["reviewer"], ROOM["members"],
                                               "reviewer"), [])

    def test_clean_removes_both_markers(self):
        self.assertEqual(rooms.clean("text\n!handoff bouwer go\n!done x"), "text")


if __name__ == "__main__":
    unittest.main()
