# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor de pure listener-logica (relay-topologie + mention-match).
Draaien vanuit agents/: `python3 -m unittest test_topology` (agents/ heeft geen
__init__.py en de modules doen top-level imports, dus het pakket-pad werkt niet).
Geen relay/netwerk nodig — `run` is een stub.
"""
import unittest

import bootstrap
import prompts
import providers
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

    def test_dedup_op_cid_bij_twee_namen(self):
        # zelfde cid onder een relay-naam en een channels.yml-naam → één entry,
        # de channels.yml-naam (canoniek) wint, geen dubbele poll.
        rows = '{"channels":[{"name":"algemeen","id":"X"},{"name":"nieuw","id":"n1"}]}'
        d = topology.poll_channels(_run({"list": rows}), {"general": "X"}, now=1000)
        cids = list(d.values())
        self.assertEqual(cids.count("X"), 1)          # X maar één keer
        self.assertIn("general", d)                    # channels.yml-naam behouden
        self.assertNotIn("algemeen", d)                # relay-alias voor dezelfde cid weg
        self.assertEqual(d["nieuw"], "n1")

    def test_lege_relay_lijst_behoudt_ontdekte_kanalen(self):
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

    def test_members_lui_bij_def_scope(self):
        # def-scope beantwoordt de vraag → member_pubs_fn mag NIET worden aangeroepen
        def boom():
            raise AssertionError("members onnodig opgehaald")
        self.assertTrue(topology.is_scoped(["general"], "general", "p", boom))


class Mentioned(unittest.TestCase):
    def test_woordgrens(self):
        self.assertTrue(prompts.mentioned("hoi @architect kijk", "architect"))
        self.assertTrue(prompts.mentioned("@architect.", "architect"))
        self.assertFalse(prompts.mentioned("kijk in @architectuur", "architect"))
        self.assertFalse(prompts.mentioned("geen mention", "architect"))
        self.assertFalse(prompts.mentioned("deploy@bouwer.example", "bouwer"))  # linker grens
        self.assertTrue(prompts.mentioned("HOI @Coordinator", "coordinator"))  # case-insens


class ChannelKnowledge(unittest.TestCase):
    def test_path_traversal_geweigerd(self):
        # onveilige (relay-geleverde) kanaalnaam mag geen bestand buiten knowledge/ lezen
        for bad in ["../../etc/passwd", "..", "a/b", "x/../y", "/etc/hosts", ""]:
            self.assertEqual(prompts.channel_knowledge("/tmp", bad), "")


if __name__ == "__main__":
    unittest.main()


class HubEnRolTest(unittest.TestCase):
    """De hub wordt op ROL gevonden. Drie plekken in de listener stonden op de
    naam `coordinator`; na de hernoeming naar odin vielen die stil terug — de
    reader op een agent met halve kanaal-zichtbaarheid, en de hub kreeg zijn
    roster- en liveness-context niet meer."""

    def _root(self, body):
        import tempfile, pathlib
        d = tempfile.mkdtemp()
        pathlib.Path(d, "identities.yml").write_text(body)
        return d

    REG = ("identities:\n"
           "  mark:\n    rol: mens\n    status: actief\n    pubkey_hex: aa\n"
           "  coordinator:\n    rol: meta-agent\n    status: ingetrokken\n    pubkey_hex: bb\n"
           "  odin:\n    rol: meta-agent\n    status: actief\n    pubkey_hex: cc\n"
           "  bouwer:\n    rol: chat-agent\n    status: actief\n    pubkey_hex: dd\n")

    def test_hub_is_de_actieve_meta_agent(self):
        self.assertEqual(bootstrap.hub_handle(self._root(self.REG)), "odin")

    def test_ingetrokken_hub_wordt_niet_gekozen(self):
        reg = self.REG.replace("  odin:\n    rol: meta-agent\n    status: actief\n    pubkey_hex: cc\n", "")
        self.assertIsNone(bootstrap.hub_handle(self._root(reg)))

    def test_roster_laat_de_hub_zelf_weg(self):
        agents = {"odin": {"system": "hub", "channels": ["general"]},
                  "bouwer": {"system": "bouwt", "channels": ["bouw"]}}
        t = prompts.roster_text(agents, "odin")
        self.assertIn("@bouwer", t)
        self.assertNotIn("@odin", t)


class LidmaatschapTest(unittest.TestCase):
    """Elke agent post óók in #statistics en #escalatie, ongeacht zijn eigen scope.
    Zonder lidmaatschap faalt die send stil — dat gebeurde: odin zat niet in
    #statistics en vijf agents niet in #escalatie."""

    CH = {"general": "c-gen", "statistics": "c-stat", "escalatie": "c-esc", "bouw": "c-bouw"}

    def test_meldt_ontbrekend_rapportagekanaal(self):
        agents = {"odin": {"channels": ["general"]}}
        leden = {"c-gen": {"pk-odin"}, "c-stat": set(), "c-esc": {"pk-odin"}}
        mis = topology.missing_memberships(agents, self.CH, {"odin": "pk-odin"}, leden.get)
        self.assertEqual(mis, [("odin", "statistics")])

    def test_meldt_ontbrekend_eigen_kanaal(self):
        agents = {"bouwer": {"channels": ["bouw"]}}
        leden = {"c-bouw": set(), "c-stat": {"pk-b"}, "c-esc": {"pk-b"}}
        mis = topology.missing_memberships(agents, self.CH, {"bouwer": "pk-b"}, leden.get)
        self.assertEqual(mis, [("bouwer", "bouw")])

    def test_niets_te_melden_als_alles_klopt(self):
        agents = {"odin": {"channels": ["general"]}}
        leden = {c: {"pk-odin"} for c in self.CH.values()}
        self.assertEqual(topology.missing_memberships(agents, self.CH, {"odin": "pk-odin"}, leden.get), [])


class ModelRapportageTest(unittest.TestCase):
    """De statistiekregel is het enige waarop je kunt aflezen of het gedeclareerde
    model afgedwongen wordt. Hij nam de EERSTE sleutel uit modelUsage; een run die
    meerdere modellen aanraakt noemde dan willekeurig één. Waargenomen 2026-09-07:
    odin werd als haiku gerapporteerd terwijl de handbook sonnet declareert."""

    def u(self, **kv):
        return {m: {"inputTokens": i, "outputTokens": 1} for m, i in kv.items()}

    def test_model_met_de_meeste_tokens_wint(self):
        usage = {"claude-haiku-4-5": {"inputTokens": 3, "outputTokens": 1},
                 "claude-sonnet-5": {"inputTokens": 900, "outputTokens": 400}}
        self.assertEqual(providers.main_model(usage, "sonnet"), "claude-sonnet-5")

    def test_volgorde_in_de_map_doet_er_niet_toe(self):
        a = {"claude-haiku-4-5": {"inputTokens": 1}, "claude-sonnet-5": {"inputTokens": 99}}
        b = {"claude-sonnet-5": {"inputTokens": 99}, "claude-haiku-4-5": {"inputTokens": 1}}
        self.assertEqual(providers.main_model(a, "sonnet"), providers.main_model(b, "sonnet"))

    def test_zonder_usage_valt_het_terug_op_wat_gevraagd_is(self):
        for leeg in (None, {}, "geen dict"):
            self.assertEqual(providers.main_model(leeg, "sonnet"), "sonnet")

    def test_alle_token_velden_tellen_mee(self):
        # cache-tokens zijn vaak veruit de grootste post; alleen inputTokens
        # vergelijken zou het verkeerde model aanwijzen.
        usage = {"a": {"inputTokens": 5}, "b": {"inputTokens": 1, "cacheReadInputTokens": 9000}}
        self.assertEqual(providers.main_model(usage, None), "b")

    def test_kosten_tellen_niet_mee_als_tokens(self):
        usage = {"a": {"inputTokens": 10}, "b": {"costUSD": 9999}}
        self.assertEqual(providers.main_model(usage, None), "a")

    def test_familie_match(self):
        self.assertTrue(providers.model_klopt("sonnet", "claude-sonnet-5"))
        self.assertTrue(providers.model_klopt("haiku", "claude-haiku-4-5-20251001"))
        self.assertFalse(providers.model_klopt("sonnet", "claude-haiku-4-5"))
        self.assertTrue(providers.model_klopt("", "wat dan ook"))   # niets gevraagd
