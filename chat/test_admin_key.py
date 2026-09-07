# SPDX-License-Identifier: EUPL-1.2
"""Kanaalbeheer tekent als orchestrator, of het gebeurt niet.

De regel die deze tests bewaken: er is geen pad waarlangs kanaal-maken,
-verwijderen of leden-toevoegen alsnog met marks mens-sleutel wordt getekend.
Ontbreekt de orchestrator-sleutel, dan is het antwoord 503 — geen stille terugval.
"""
import importlib
import os
import unittest


class AdminKeyTest(unittest.TestCase):
    def _load(self, orch_key):
        if orch_key is None:
            os.environ.pop("BUZZ_ORCHESTRATOR_KEY", None)
        else:
            os.environ["BUZZ_ORCHESTRATOR_KEY"] = orch_key
        import buzzcli
        return importlib.reload(buzzcli)

    def tearDown(self):
        os.environ.pop("BUZZ_ORCHESTRATOR_KEY", None)

    def test_zonder_sleutel_is_beheer_uit(self):
        b = self._load(None)
        rc, _out, err = b.buzz_admin(["channels", "list"])
        self.assertIsNone(rc)                 # None = "niet geprobeerd"
        self.assertIn("BUZZ_ORCHESTRATOR_KEY", err)

    def test_met_sleutel_tekent_de_aanroep_met_die_sleutel(self):
        b = self._load("nsec-orchestrator")
        seen = {}

        def fake_run(cmd, **kw):
            seen["key"] = (kw.get("env") or {}).get("BUZZ_PRIVATE_KEY")

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()

        orig = b.subprocess.run
        b.subprocess.run = fake_run
        try:
            b.buzz_admin(["channels", "create", "--name", "x"])
        finally:
            b.subprocess.run = orig
        self.assertEqual(seen["key"], "nsec-orchestrator")

    def test_gewone_buzz_gebruikt_de_procesidentiteit(self):
        b = self._load("nsec-orchestrator")
        seen = {}

        def fake_run(cmd, **kw):
            seen["env"] = kw.get("env")

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()

        orig = b.subprocess.run
        b.subprocess.run = fake_run
        try:
            b.buzz(["messages", "send"])
        finally:
            b.subprocess.run = orig
        self.assertIsNone(seen["env"])  # geen override → mark blijft de afzender


if __name__ == "__main__":
    unittest.main()


class HubLookupTest(unittest.TestCase):
    """De hub wordt op ROL gevonden, niet op naam — anders breekt elke hernoeming
    het toevoegen van de hub aan een nieuw kanaal, en wel STIL (de add is
    best-effort). Precies dat gebeurde na coordinator -> odin."""

    def _map(self, text):
        import roster
        return roster._parse_identities(text)

    REG = (
        "identities:\n"
        "  mark:\n    rol: mens\n    status: actief\n    pubkey_hex: aa\n"
        "  coordinator:\n    rol: meta-agent\n    status: ingetrokken\n    pubkey_hex: bb\n"
        "  odin:\n    rol: meta-agent\n    status: actief\n    pubkey_hex: cc\n"
    )

    def test_ingetrokken_hub_telt_niet_mee(self):
        m = self._map(self.REG)
        metas = [pk for pk, i in m.items() if i.get("rol") == "meta-agent"]
        self.assertEqual(metas, ["cc"])          # odin, niet de ingetrokken coordinator

    def test_hernoeming_breekt_de_lookup_niet(self):
        # zelfde registry, andere naam voor dezelfde rol
        m = self._map(self.REG.replace("  odin:", "  wodan:"))
        metas = [i["name"] for i in m.values() if i.get("rol") == "meta-agent"]
        self.assertEqual(metas, ["wodan"])
