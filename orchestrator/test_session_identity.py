# SPDX-License-Identifier: MIT
"""create-session-identity: the phase split, #general, and the guards on what
reaches ssh and buzz. No keys, SOPS or relay: run, decrypt, the key maker and
derive are replaced, and every external call is recorded."""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import session_identity as si  # noqa: E402

_spec = importlib.util.spec_from_file_location("csi", os.path.join(HERE, "create-session-identity.py"))
csi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(csi)

PUB = "ab" * 32
CHANS = {"general": {"id": "g"}, "escalatie": {"id": "e"}, "statistics": {"id": "s"},
         "marketing": {"id": "m", "archived": "2026-10-22"}}
REG = {"heimdall": {"rol": "sessie", "status": "actief", "pubkey_hex": PUB},
       "mark": {"rol": "mens", "status": "actief", "pubkey_hex": "cd" * 32},
       "odin": {"rol": "meta-agent", "status": "actief", "pubkey_hex": "ef" * 32},
       "hub": {"rol": "sessie", "status": "ingetrokken", "pubkey_hex": "01" * 32}}
SEC = {n: {"privkey_hex": "11" * 32, "nsec": "nsec1" + n} for n in list(REG) + ["orchestrator"]}


def derive_ok(entry):
    return {"nsec1heimdall": PUB}.get(entry["nsec"])


class Guards(unittest.TestCase):
    def test_name(self):
        for good in ("heimdall", "odin-worker", "a1"):
            self.assertEqual(si.check_name(good), good)
        for bad in ("Heimdall", "h", "1abc", "a;rm", "a b", "", "x" * 32, "../x"):
            self.assertRaises(si.Refused, si.check_name, bad)

    def test_registry_is_the_default_and_relay_needs_the_owner_step(self):
        self.assertEqual(csi.parse(["--name", "x"]).phase, "registry")
        self.assertEqual(si.check_phase("registry", False), "registry")
        for p in ("relay", "all"):
            with self.assertRaises(si.Refused) as c:
                si.check_phase(p, False)
            self.assertIn("Mark's step", str(c.exception))
            self.assertEqual(si.check_phase(p, True), p)

    def test_channels_escalatie_first_general_refused(self):
        self.assertEqual(si.channel_ids(["statistics"], CHANS), [("escalatie", "e"), ("statistics", "s")])
        self.assertEqual(si.channel_ids(["escalatie"], CHANS), [("escalatie", "e")])
        for bad in (["general"], ["nope"], ["marketing"]):
            self.assertRaises(si.Refused, si.channel_ids, bad, CHANS)

    def test_relay_target_only_an_active_session(self):
        self.assertEqual(si.relay_target("heimdall", REG, SEC, derive_ok), (PUB, "nsec1heimdall"))
        for n in ("mark", "odin", "hub", "nobody"):
            self.assertRaises(si.Refused, si.relay_target, n, REG, SEC, derive_ok)

    def test_relay_target_pubkey_must_be_hex_and_match_the_key(self):
        for pub in ("abc; touch /tmp/x", PUB.upper(), PUB + "00", PUB[:-1] + " ", 123):
            reg = {"heimdall": dict(REG["heimdall"], pubkey_hex=pub)}
            self.assertRaises(si.Refused, si.relay_target, "heimdall", reg, SEC, derive_ok)
        self.assertRaises(si.Refused, si.relay_target, "heimdall", REG, SEC, lambda e: "cd" * 32)
        self.assertRaises(si.Refused, si.relay_target, "heimdall", REG, SEC, lambda e: None)
        self.assertRaises(si.Refused, si.relay_target, "heimdall", REG, {}, derive_ok)


class Phases(unittest.TestCase):
    """main() end to end with every outside call recorded."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        os.mkdir(os.path.join(root, "secrets"))
        import yaml
        yaml.safe_dump({"channels": CHANS}, open(os.path.join(root, "channels.yml"), "w"))
        yaml.safe_dump({"identities": {k: dict(v) for k, v in REG.items()}},
                       open(os.path.join(root, "identities.yml"), "w"))
        self.calls, self.envs, self.stored = [], [], []
        ok = mock.Mock(returncode=0, stdout='{"accepted": true}', stderr="")
        self.patches = [
            mock.patch.object(csi, "BOOMHUIS", root),
            mock.patch.object(csi, "run", side_effect=lambda cmd, env=None, **k: self.calls.append(cmd) or self.envs.append(env) or ok),
            mock.patch.object(csi, "decrypt", side_effect=lambda p: {"identities": {
                k: dict(v) for k, v in SEC.items()}}),
            mock.patch.object(csi, "store_secret", side_effect=lambda *a: self.stored.append(a)),
            mock.patch.object(csi, "npub_nsec", return_value=("12" * 32, "npub1new", "33" * 32, "nsec1new")),
            mock.patch.object(csi, "derive", side_effect=derive_ok),
            mock.patch.object(csi.time, "sleep"),
            mock.patch("sys.stdout", new_callable=io.StringIO),  # keep verify.sh's tail clean
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def registry(self):
        import yaml
        return yaml.safe_load(open(os.path.join(self.tmp.name, "identities.yml")))["identities"]

    def test_default_phase_writes_key_and_registry_and_touches_no_relay(self):
        csi.main(["--name", "newbie", "--display", "Newbie", "--chan", "statistics"])
        self.assertEqual(len(self.stored), 1)
        self.assertEqual(self.registry()["newbie"]["rol"], "sessie")
        self.assertEqual(self.registry()["newbie"]["display_name"], "Newbie")
        self.assertEqual(self.calls, [])

    def test_relay_without_owner_step_does_nothing(self):
        with self.assertRaises(SystemExit):
            csi.main(["--name", "heimdall", "--phase", "relay"])
        self.assertEqual((self.calls, self.stored), ([], []))

    def test_general_is_refused_before_anything(self):
        with self.assertRaises(SystemExit):
            csi.main(["--name", "newbie", "--chan", "general"])
        self.assertEqual((self.calls, self.stored), ([], []))

    def test_owner_step_refuses_mark_and_odin(self):
        for n in ("mark", "odin", "hub"):
            with self.assertRaises(SystemExit):
                csi.main(["--name", n, "--phase", "relay", "--owner-step"])
        self.assertEqual(self.calls, [])

    def test_owner_step_refuses_a_tampered_pubkey(self):
        import yaml
        reg = {k: dict(v) for k, v in REG.items()}
        reg["heimdall"]["pubkey_hex"] = "abc; touch /tmp/pwned"
        yaml.safe_dump({"identities": reg}, open(os.path.join(self.tmp.name, "identities.yml"), "w"))
        with self.assertRaises(SystemExit):
            csi.main(["--name", "heimdall", "--phase", "relay", "--owner-step"])
        self.assertEqual(self.calls, [])

    def test_owner_step_adds_relay_and_channels_signed_by_orchestrator(self):
        csi.main(["--name", "heimdall", "--chan", "statistics", "--phase", "relay", "--owner-step"])
        ssh, esc, stat, prof = self.calls
        self.assertEqual(ssh[:3], ["ssh", "-o", "BatchMode=yes"])
        self.assertIn(PUB, ssh)
        self.assertEqual([esc[4], stat[4]], ["e", "s"])
        self.assertEqual(prof[1:3], ["users", "set-profile"])
        keys = [(e or {}).get("BUZZ_PRIVATE_KEY") for e in self.envs]
        self.assertEqual(keys, [None, "nsec1orchestrator", "nsec1orchestrator", "nsec1heimdall"])
        self.assertEqual(self.stored, [])


if __name__ == "__main__":
    unittest.main()
