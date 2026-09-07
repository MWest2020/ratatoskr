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
