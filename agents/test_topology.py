# SPDX-License-Identifier: EUPL-1.2
"""Offline tests for `topology.py` (relay topology: channels, members, scope).
Run from agents/: `python3 -m unittest test_topology` (agents/ has no __init__.py
and the modules use top-level imports, so the package path does not work).
No relay or network needed — `run` is a stub.
"""
import unittest

import topology


def _run(mapping):
    """Stub `run(args)`: returns the prepared stdout per subcommand."""
    def run(args):
        key = args[1]  # 'list' of 'members'
        return mapping.get(key, "")
    return run


class PollChannels(unittest.TestCase):
    def setUp(self):
        topology._channels.update(t=0.0, data=None)  # empty cache per test

    def test_hide_fallback_wins_and_new_channel(self):
        rows = ('{"channels":[{"name":"general","id":"WRONG"},'
                '{"name":"welcome-everyone","id":"junk"},'
                '{"name":"nieuw","id":"n1"},{"name":"red-team","id":"rt"}]}')
        fb = {"general": "goed", "red-team": "rt", "escalatie": "e"}
        d = topology.poll_channels(_run({"list": rows}), fb, now=1000)
        self.assertEqual(d["general"], "goed")        # the channels.yml cid wins
        self.assertNotIn("welcome-everyone", d)        # _HIDE
        self.assertEqual(d["nieuw"], "n1")             # genuinely new channel added
        self.assertEqual(d["escalatie"], "e")

    def test_failed_fetch_keeps_a_good_cache(self):
        fb = {"general": "g"}
        rows = '{"channels":[{"name":"nieuw","id":"n1"}]}'
        topology.poll_channels(_run({"list": rows}), fb, now=1000)
        topology._channels["t"] = 0.0  # force an expired cache
        d = topology.poll_channels(_run({"list": ""}), fb, now=2000)  # empty fetch
        self.assertEqual(d.get("nieuw"), "n1")  # did not fall back to the bare fallback

    def test_no_cache_and_an_error_falls_back(self):
        fb = {"general": "g"}
        d = topology.poll_channels(_run({"list": ""}), fb, now=1000)
        self.assertEqual(d, fb)

    def test_dedup_on_cid_for_two_names(self):
        # the same cid under a relay name and a channels.yml name → one entry,
        # the channels.yml name (canonical) wins, no double poll.
        rows = '{"channels":[{"name":"algemeen","id":"X"},{"name":"nieuw","id":"n1"}]}'
        d = topology.poll_channels(_run({"list": rows}), {"general": "X"}, now=1000)
        cids = list(d.values())
        self.assertEqual(cids.count("X"), 1)          # X only once
        self.assertIn("general", d)                    # channels.yml name kept
        self.assertNotIn("algemeen", d)                # relay alias for the same cid gone
        self.assertEqual(d["nieuw"], "n1")

    def test_empty_relay_list_keeps_discovered_channels(self):
        # succeeded-but-empty ({"channels":[]}) is never legitimate → keep the good
        # cache, do not fall back to fallback-only (losing a discovered channel).
        fb = {"general": "g"}
        topology.poll_channels(_run({"list": '{"channels":[{"name":"nieuw","id":"n1"}]}'}), fb, now=1000)
        topology._channels["t"] = 0.0  # expired
        d = topology.poll_channels(_run({"list": '{"channels":[]}'}), fb, now=2000)
        self.assertEqual(d.get("nieuw"), "n1")


class Members(unittest.TestCase):
    def setUp(self):
        topology._members.clear()

    def test_empty_channel_is_cached(self):
        run = _run({"members": '{"members":[{"pubkey":"a"}]}'})
        self.assertEqual(topology.members(run, "c", now=1000), {"a"})
        topology._members["c"]["t"] = 0.0  # expired
        run2 = _run({"members": '{"members":[]}'})  # legitimately empty (last member gone)
        self.assertEqual(topology.members(run2, "c", now=2000), set())

    def test_failed_fetch_keeps_members(self):
        run = _run({"members": '{"members":[{"pubkey":"a"}]}'})
        topology.members(run, "c", now=1000)
        topology._members["c"]["t"] = 0.0
        self.assertEqual(topology.members(_run({"members": ""}), "c", now=2000), {"a"})

    def test_first_failed_fetch_does_not_cache_negatively(self):
        # no earlier entry + failed fetch → return set(), but do NOT cache it, so a
        # member appearing right after does not stay invisible for 60s.
        self.assertEqual(topology.members(_run({"members": ""}), "x", now=1000), set())
        self.assertNotIn("x", topology._members)
        got = topology.members(_run({"members": '{"members":[{"pubkey":"a"}]}'}), "x", now=1001)
        self.assertEqual(got, {"a"})


class Rows(unittest.TestCase):
    def test_non_dict_gives_none_not_a_crash(self):
        # rc=0 with 'null' or a bare string must not raise AttributeError
        self.assertIsNone(topology._rows("null", "channels"))
        self.assertIsNone(topology._rows('"hoi"', "channels"))
        self.assertIsNone(topology._rows("", "channels"))
        self.assertIsNone(topology._rows('{"error":"boom"}', "members"))  # key absent
        self.assertIsNone(topology._rows('{"channels":{"a":1}}', "channels"))  # not a list
        self.assertIsNone(topology._rows('{"channels":"x"}', "channels"))      # not a list
        self.assertEqual(topology._rows('{"members":[]}', "members"), [])  # empty ≠ error
        self.assertEqual(topology._rows('{"channels":[1]}', "channels"), [1])
        self.assertEqual(topology._rows("[1,2]", "channels"), [1, 2])


class IsScoped(unittest.TestCase):
    def test_union(self):
        self.assertTrue(topology.is_scoped(["general"], "general", "p", lambda: set()))
        self.assertTrue(topology.is_scoped(["general"], "red-team", "p", lambda: {"p"}))
        self.assertFalse(topology.is_scoped(["general"], "red-team", "p", lambda: {"q"}))

    def test_members_lazy_on_def_scope(self):
        # the def scope answers the question → member_pubs_fn must NOT be called
        def boom():
            raise AssertionError("members fetched unnecessarily")
        self.assertTrue(topology.is_scoped(["general"], "general", "p", boom))


class MembershipTest(unittest.TestCase):
    """Every agent also posts in #statistics and #escalatie, regardless of its own
    scope. Without membership that send fails silently — which happened: odin was
    not in #statistics and five agents were not in #escalatie."""

    CH = {"general": "c-gen", "statistics": "c-stat", "escalatie": "c-esc", "bouw": "c-bouw"}

    def test_reports_a_missing_report_channel(self):
        agents = {"odin": {"channels": ["general"]}}
        members = {"c-gen": {"pk-odin"}, "c-stat": set(), "c-esc": {"pk-odin"}}
        missing = topology.missing_memberships(agents, self.CH, {"odin": "pk-odin"}, members.get)
        self.assertEqual(missing, [("odin", "statistics")])

    def test_reports_a_missing_own_channel(self):
        agents = {"bouwer": {"channels": ["bouw"]}}
        members = {"c-bouw": set(), "c-stat": {"pk-b"}, "c-esc": {"pk-b"}}
        missing = topology.missing_memberships(agents, self.CH, {"bouwer": "pk-b"}, members.get)
        self.assertEqual(missing, [("bouwer", "bouw")])

    def test_nothing_to_report_when_all_is_well(self):
        agents = {"odin": {"channels": ["general"]}}
        members = {c: {"pk-odin"} for c in self.CH.values()}
        self.assertEqual(topology.missing_memberships(agents, self.CH, {"odin": "pk-odin"}, members.get), [])


if __name__ == "__main__":
    unittest.main()
