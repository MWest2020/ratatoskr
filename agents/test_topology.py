# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor de pure listener-logica (relay-topologie + mention-match).
Draaien vanuit agents/: `python3 -m unittest test_topology` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
Geen relay/netwerk nodig — `run` is een stub.
"""
import unittest

import prompts
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

    def test_hide_fallback_wint_en_nieuw_kanaal(self):
        rows = ('{"channels":[{"name":"general","id":"WRONG"},'
                '{"name":"welcome-everyone","id":"junk"},'
                '{"name":"nieuw","id":"n1"},{"name":"red-team","id":"rt"}]}')
        fb = {"general": "goed", "red-team": "rt", "escalatie": "e"}
        d = topology.poll_channels(_run({"list": rows}), fb, now=1000)
        self.assertEqual(d["general"], "goed")        # channels.yml-cid wint
        self.assertNotIn("welcome-everyone", d)        # _HIDE
        self.assertEqual(d["nieuw"], "n1")             # echt-nieuw kanaal erbij
        self.assertEqual(d["escalatie"], "e")

    def test_mislukte_fetch_behoudt_goede_cache(self):
        fb = {"general": "g"}
        rows = '{"channels":[{"name":"nieuw","id":"n1"}]}'
        topology.poll_channels(_run({"list": rows}), fb, now=1000)
        topology._channels["t"] = 0.0  # forceer verlopen cache
        d = topology.poll_channels(_run({"list": ""}), fb, now=2000)  # lege fetch
        self.assertEqual(d.get("nieuw"), "n1")  # niet teruggevallen op kale fallback

    def test_geen_cache_en_fout_valt_op_fallback(self):
        fb = {"general": "g"}
        d = topology.poll_channels(_run({"list": ""}), fb, now=1000)
        self.assertEqual(d, fb)


class Members(unittest.TestCase):
    def setUp(self):
        topology._members.clear()

    def test_leeg_kanaal_wordt_gecachet(self):
        run = _run({"members": '{"members":[{"pubkey":"a"}]}'})
        self.assertEqual(topology.members(run, "c", now=1000), {"a"})
        topology._members["c"]["t"] = 0.0  # verlopen
        run2 = _run({"members": '{"members":[]}'})  # legit leeg (laatste lid weg)
        self.assertEqual(topology.members(run2, "c", now=2000), set())

    def test_mislukte_fetch_behoudt_leden(self):
        run = _run({"members": '{"members":[{"pubkey":"a"}]}'})
        topology.members(run, "c", now=1000)
        topology._members["c"]["t"] = 0.0
        self.assertEqual(topology.members(_run({"members": ""}), "c", now=2000), {"a"})

    def test_eerste_mislukte_fetch_cachet_niet_negatief(self):
        # geen eerdere entry + mislukte fetch → set() teruggeven, maar NIET cachen,
        # zodat een lid dat direct daarna verschijnt niet 60s onzichtbaar blijft.
        self.assertEqual(topology.members(_run({"members": ""}), "x", now=1000), set())
        self.assertNotIn("x", topology._members)
        got = topology.members(_run({"members": '{"members":[{"pubkey":"a"}]}'}), "x", now=1001)
        self.assertEqual(got, {"a"})


class Rows(unittest.TestCase):
    def test_non_dict_geeft_none_geen_crash(self):
        # rc=0 met 'null' of een bare string mag geen AttributeError geven
        self.assertIsNone(topology._rows("null", "channels"))
        self.assertIsNone(topology._rows('"hoi"', "channels"))
        self.assertIsNone(topology._rows("", "channels"))
        self.assertEqual(topology._rows('{"channels":[1]}', "channels"), [1])
        self.assertEqual(topology._rows("[1,2]", "channels"), [1, 2])


class IsScoped(unittest.TestCase):
    def test_union(self):
        self.assertTrue(topology.is_scoped(["general"], "general", "p", set()))   # def
        self.assertTrue(topology.is_scoped(["general"], "red-team", "p", {"p"}))   # lid
        self.assertFalse(topology.is_scoped(["general"], "red-team", "p", {"q"}))  # geen van beide


class Mentioned(unittest.TestCase):
    def test_woordgrens(self):
        self.assertTrue(prompts.mentioned("hoi @architect kijk", "architect"))
        self.assertTrue(prompts.mentioned("@architect.", "architect"))
        self.assertFalse(prompts.mentioned("kijk in @architectuur", "architect"))
        self.assertFalse(prompts.mentioned("geen mention", "architect"))
        self.assertFalse(prompts.mentioned("deploy@bouwer.example", "bouwer"))  # linker grens
        self.assertTrue(prompts.mentioned("HOI @Coordinator", "coordinator"))  # case-insens


if __name__ == "__main__":
    unittest.main()
