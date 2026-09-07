# SPDX-License-Identifier: EUPL-1.2
"""De actielaag: wie tekent wat, en wat gebeurt er als de relay nee zegt.

Twee dingen die hier echt misgingen en die deze tests vastzetten:
kanaalbeheer mag NOOIT met marks sleutel getekend worden (fail-closed i.p.v.
terugvallen), en de hub wordt op rol gezocht — op naam brak dat stil na de
hernoeming coordinator -> odin, waarna elk nieuw kanaal zonder hub ontstond.
"""
import json
import unittest

import actions
import buzzcli
import roster


class Nep:
    """Vervangt buzz/buzz_admin en onthoudt de aanroepen."""

    def __init__(self, antwoord=(0, "", ""), admin_uit=False):
        self.antwoord, self.admin_uit, self.calls = antwoord, admin_uit, []

    def buzz(self, args, stdin=None, timeout=25, key=None):
        self.calls.append(("buzz", args, key))
        return self.antwoord

    def admin(self, args, stdin=None, timeout=25):
        self.calls.append(("admin", args, None))
        if self.admin_uit:
            return None, "", buzzcli.ADMIN_OFF
        return self.antwoord


class Basis(unittest.TestCase):
    def zet(self, nep, cids=("c1",), agents=None, hub="pk-odin"):
        self.oud = (actions.buzz, actions.buzz_admin, actions.valid_cid,
                    roster.agent_pubkey, roster.hub_pubkey, actions.channel_member_pubkeys)
        actions.buzz, actions.buzz_admin = nep.buzz, nep.admin
        actions.valid_cid = lambda c: c in cids
        actions.channel_member_pubkeys = lambda c: {"pk-lid": "member"}
        roster.agent_pubkey = lambda n: (agents or {}).get(n)
        roster.hub_pubkey = lambda: hub

    def tearDown(self):
        (actions.buzz, actions.buzz_admin, actions.valid_cid,
         roster.agent_pubkey, roster.hub_pubkey, actions.channel_member_pubkeys) = self.oud


class KanaalBeheerTest(Basis):
    def test_create_tekent_als_orchestrator_niet_als_mark(self):
        nep = Nep((0, json.dumps({"channel_id": "nieuw"}), ""))
        self.zet(nep)
        code, _ = actions.create_channel("bouwoverleg")
        self.assertEqual(code, 200)
        soorten = {c[0] for c in nep.calls}
        self.assertEqual(soorten, {"admin"})          # geen enkele gewone buzz-call

    def test_zonder_orchestrator_sleutel_geen_stille_terugval(self):
        nep = Nep(admin_uit=True)
        self.zet(nep)
        code, payload = actions.create_channel("bouwoverleg")
        self.assertEqual(code, 503)
        self.assertIn("BUZZ_ORCHESTRATOR_KEY", payload["error"])
        self.assertNotIn("buzz", {c[0] for c in nep.calls})   # niets met marks sleutel

    def test_naam_wordt_gevalideerd_voor_de_relay(self):
        nep = Nep(); self.zet(nep)
        for naam in ("", "met spatie", "a" * 40, "-begintfout", "../x", "a/b"):
            code, _ = actions.create_channel(naam)
            self.assertEqual(code, 400, naam)
        self.assertEqual(nep.calls, [])               # niets bereikte de relay

    def test_hoofdletters_en_spaties_worden_genormaliseerd(self):
        # Bewust géén fout: de gebruiker typt "Bouw " en krijgt #bouw.
        nep = Nep((0, json.dumps({"channel_id": "n"}), "")); self.zet(nep)
        code, payload = actions.create_channel("  Bouw  ")
        self.assertEqual((code, payload["name"]), (200, "bouw"))

    def test_hub_wordt_toegevoegd_aan_een_nieuw_kanaal(self):
        nep = Nep((0, json.dumps({"channel_id": "nieuw"}), ""))
        self.zet(nep)
        _, payload = actions.create_channel("bouwoverleg")
        self.assertTrue(payload["hub_added"])
        add = [c for c in nep.calls if c[1][:2] == ["channels", "add-member"]]
        self.assertEqual(add[0][1][5], "pk-odin")     # --pubkey van de hub

    def test_zonder_hub_faalt_de_create_niet(self):
        # De add is best-effort: het kanaal bestaat al. Wél zichtbaar in het antwoord.
        nep = Nep((0, json.dumps({"channel_id": "nieuw"}), ""))
        self.zet(nep, hub=None)
        code, payload = actions.create_channel("bouwoverleg")
        self.assertEqual(code, 200)
        self.assertFalse(payload["hub_added"])


class AgentToevoegenTest(Basis):
    def test_alleen_bekende_agents(self):
        nep = Nep(); self.zet(nep, agents={"bouwer": "pk-b"})
        self.assertEqual(actions.add_agent("c1", "onbekend")[0], 404)
        self.assertEqual(nep.calls, [])

    def test_onbekend_kanaal_wordt_geweigerd(self):
        nep = Nep(); self.zet(nep, agents={"bouwer": "pk-b"})
        self.assertEqual(actions.add_agent("bestaat-niet", "bouwer")[0], 400)

    def test_toevoegen_tekent_als_orchestrator(self):
        nep = Nep(); self.zet(nep, agents={"bouwer": "pk-b"})
        self.assertEqual(actions.add_agent("c1", "bouwer")[0], 200)
        self.assertEqual({c[0] for c in nep.calls}, {"admin"})


class SendTest(Basis):
    def test_lege_inhoud_bereikt_de_relay_niet(self):
        nep = Nep(); self.zet(nep)
        self.assertEqual(actions.send("c1", "   ")[0], 400)
        self.assertEqual(nep.calls, [])

    def test_onbekend_kanaal_wordt_geweigerd(self):
        nep = Nep(); self.zet(nep)
        self.assertEqual(actions.send("weg", "hoi")[0], 400)

    def test_bericht_tekent_met_de_procesidentiteit(self):
        nep = Nep(); self.zet(nep)
        self.assertEqual(actions.send("c1", "hoi")[0], 200)
        self.assertEqual({c[0] for c in nep.calls}, {"buzz"})   # mark, niet de orchestrator

    def test_onbekende_mention_geeft_een_keuze_terug(self):
        fout = (1, "", "mention '@bouwer' does not match any channel member")
        nep = Nep(fout); self.zet(nep, agents={"bouwer": "pk-b"})
        code, payload = actions.send("c1", "hoi @bouwer")
        self.assertEqual(code, 409)
        self.assertEqual(payload["missing_agent"], "bouwer")
        self.assertTrue(payload["known"])            # bestaat -> "toevoegen" mag
        self.assertTrue(payload["can_force"])

    def test_onbekende_mention_die_geen_agent_is(self):
        fout = (1, "", "mention '@niemand' does not match any channel member")
        nep = Nep(fout); self.zet(nep, agents={})
        _, payload = actions.send("c1", "hoi @niemand")
        self.assertFalse(payload["known"])           # alleen "toch versturen"

    def test_force_hangt_een_echt_lid_als_anker(self):
        nep = Nep(); self.zet(nep)
        actions.send("c1", "hoi @here", force=True)
        args = nep.calls[0][1]
        self.assertIn("--mention", args)
        self.assertEqual(args[args.index("--mention") + 1], "pk-lid")

    def test_andere_relayfout_blijft_een_502(self):
        nep = Nep((1, "", "relay down")); self.zet(nep)
        code, payload = actions.send("c1", "hoi")
        self.assertEqual(code, 502)
        self.assertIn("relay down", payload["error"])


if __name__ == "__main__":
    unittest.main()
