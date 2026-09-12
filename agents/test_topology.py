# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor `topology.py` (relay-topologie: kanalen, leden, scope).
Draaien vanuit agents/: `python3 -m unittest test_topology` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
Geen relay/netwerk nodig — `run` is een stub.
"""
import unittest

import topology


def _run(mapping):
    """Stub-`run(args)`: geeft de vooraf-bepaalde stdout per subcommando."""
    def run(args):
        key = args[1]  # 'list' of 'members'
        return mapping.get(key, "")
    return run


class PollChannels(unittest.TestCase):
    def setUp(self):
        topology._channels.update(t=0.0, data=None)  # cache leeg per test

    def test_hide_fallback_wins_and_new_channel(self):
        rows = ('{"channels":[{"name":"general","id":"WRONG"},'
                '{"name":"welcome-everyone","id":"junk"},'
                '{"name":"nieuw","id":"n1"},{"name":"red-team","id":"rt"}]}')
        fb = {"general": "goed", "red-team": "rt", "escalatie": "e"}
        d = topology.poll_channels(_run({"list": rows}), fb, now=1000)
        self.assertEqual(d["general"], "goed")        # channels.yml-cid wint
        self.assertNotIn("welcome-everyone", d)        # _HIDE
        self.assertEqual(d["nieuw"], "n1")             # echt-nieuw kanaal erbij
        self.assertEqual(d["escalatie"], "e")

    def test_failed_fetch_keeps_a_good_cache(self):
        fb = {"general": "g"}
        rows = '{"channels":[{"name":"nieuw","id":"n1"}]}'
        topology.poll_channels(_run({"list": rows}), fb, now=1000)
        topology._channels["t"] = 0.0  # forceer verlopen cache
        d = topology.poll_channels(_run({"list": ""}), fb, now=2000)  # lege fetch
        self.assertEqual(d.get("nieuw"), "n1")  # niet teruggevallen op kale fallback

    def test_no_cache_and_an_error_falls_back(self):
        fb = {"general": "g"}
        d = topology.poll_channels(_run({"list": ""}), fb, now=1000)
        self.assertEqual(d, fb)

    def test_dedup_on_cid_for_two_names(self):
        # zelfde cid onder een relay-naam en een channels.yml-naam → één entry,
        # de channels.yml-naam (canoniek) wint, geen dubbele poll.
        rows = '{"channels":[{"name":"algemeen","id":"X"},{"name":"nieuw","id":"n1"}]}'
        d = topology.poll_channels(_run({"list": rows}), {"general": "X"}, now=1000)
        cids = list(d.values())
        self.assertEqual(cids.count("X"), 1)          # X maar één keer
        self.assertIn("general", d)                    # channels.yml-naam behouden
        self.assertNotIn("algemeen", d)                # relay-alias voor dezelfde cid weg
        self.assertEqual(d["nieuw"], "n1")

    def test_empty_relay_list_keeps_discovered_channels(self):
        # geslaagd-maar-leeg ({"channels":[]}) is nooit legitiem → goede cache houden,
        # niet terugvallen op fallback-only (verlies van een ontdekt kanaal).
        fb = {"general": "g"}
        topology.poll_channels(_run({"list": '{"channels":[{"name":"nieuw","id":"n1"}]}'}), fb, now=1000)
        topology._channels["t"] = 0.0  # verlopen
        d = topology.poll_channels(_run({"list": '{"channels":[]}'}), fb, now=2000)
        self.assertEqual(d.get("nieuw"), "n1")


class Members(unittest.TestCase):
    def setUp(self):
        topology._members.clear()

    def test_empty_channel_is_cached(self):
        run = _run({"members": '{"members":[{"pubkey":"a"}]}'})
        self.assertEqual(topology.members(run, "c", now=1000), {"a"})
        topology._members["c"]["t"] = 0.0  # verlopen
        run2 = _run({"members": '{"members":[]}'})  # legit leeg (laatste lid weg)
        self.assertEqual(topology.members(run2, "c", now=2000), set())

    def test_failed_fetch_keeps_members(self):
        run = _run({"members": '{"members":[{"pubkey":"a"}]}'})
        topology.members(run, "c", now=1000)
        topology._members["c"]["t"] = 0.0
        self.assertEqual(topology.members(_run({"members": ""}), "c", now=2000), {"a"})

    def test_first_failed_fetch_does_not_cache_negatively(self):
        # geen eerdere entry + mislukte fetch → set() teruggeven, maar NIET cachen,
        # zodat een lid dat direct daarna verschijnt niet 60s onzichtbaar blijft.
        self.assertEqual(topology.members(_run({"members": ""}), "x", now=1000), set())
        self.assertNotIn("x", topology._members)
        got = topology.members(_run({"members": '{"members":[{"pubkey":"a"}]}'}), "x", now=1001)
        self.assertEqual(got, {"a"})


class Rows(unittest.TestCase):
    def test_non_dict_gives_none_not_a_crash(self):
        # rc=0 met 'null' of een bare string mag geen AttributeError geven
        self.assertIsNone(topology._rows("null", "channels"))
        self.assertIsNone(topology._rows('"hoi"', "channels"))
        self.assertIsNone(topology._rows("", "channels"))
        self.assertIsNone(topology._rows('{"error":"boom"}', "members"))  # sleutel afwezig
        self.assertIsNone(topology._rows('{"channels":{"a":1}}', "channels"))  # geen lijst
        self.assertIsNone(topology._rows('{"channels":"x"}', "channels"))      # geen lijst
        self.assertEqual(topology._rows('{"members":[]}', "members"), [])  # leeg ≠ fout
        self.assertEqual(topology._rows('{"channels":[1]}', "channels"), [1])
        self.assertEqual(topology._rows("[1,2]", "channels"), [1, 2])


class IsScoped(unittest.TestCase):
    def test_union(self):
        self.assertTrue(topology.is_scoped(["general"], "general", "p", lambda: set()))
        self.assertTrue(topology.is_scoped(["general"], "red-team", "p", lambda: {"p"}))
        self.assertFalse(topology.is_scoped(["general"], "red-team", "p", lambda: {"q"}))

    def test_members_lazy_on_def_scope(self):
        # def-scope beantwoordt de vraag → member_pubs_fn mag NIET worden aangeroepen
        def boom():
            raise AssertionError("members onnodig opgehaald")
        self.assertTrue(topology.is_scoped(["general"], "general", "p", boom))


class MembershipTest(unittest.TestCase):
    """Elke agent post óók in #statistics en #escalatie, ongeacht zijn eigen scope.
    Zonder lidmaatschap faalt die send stil — dat gebeurde: odin zat niet in
    #statistics en vijf agents niet in #escalatie."""

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
