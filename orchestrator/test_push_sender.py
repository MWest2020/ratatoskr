# SPDX-License-Identifier: EUPL-1.2
"""De verzender: een leesfout mag nooit als "0 abonnees" doorgaan.

Apart bestand van `test_push_chain.py` omdat het over de andere kant van de naad
gaat — en omdat dat bestand anders over de regelgrens van 200 heen ging.

De storing die dit vastpint is de vervelendste soort: de verzender meldt
"niets te versturen, klaar", en dat is precies de uitkomst die niemand
onderzoekt. Een onbereikbare host, een geweigerde sudo en kapotte JSON moeten
alle drie hard stoppen.
"""
import importlib.machinery
import importlib.util
import json
import os
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SUB = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc",
       "keys": {"p256dh": "p" * 20, "auth": "a" * 16}}


class AReadErrorIsNeverZeroSubscribers(unittest.TestCase):
    """Storing 3: de verzender mag een fout nooit als '0 abonnees' lezen.

    Een verzender die dan 'niets te versturen' meldt, meldt succes terwijl er
    niemand bereikt is — en dat is de enige uitkomst die je nooit onderzoekt.
    """

    def setUp(self):
        try:
            import pywebpush  # noqa: F401
        except ImportError:
            self.skipTest("pywebpush niet beschikbaar — draai met --with pywebpush")
        self.mod = _load("push_notify", os.path.join(HERE, "push-notify.py"))

    def tearDown(self):
        if getattr(self, "echt", None) is not None:
            self.mod.subprocess = self.echt

    def _with_ssh(self, rc, stdout="", stderr=""):
        """Vervang subprocess ALLEEN op deze module.

        De eerste versie deed `self.mod.subprocess.run = ...`, en omdat
        push-notify.py een kale `import subprocess` doet, is `self.mod.subprocess`
        het echte subprocess-module-object: die toewijzing sloopte
        `subprocess.run` voor het hele proces en voor elke test die daarna liep.
        Drie andere tests in deze map vielen daardoor om — en ze vielen om met
        JSON-fouten die niets met hun eigen onderwerp te maken hadden, dus je
        zoekt op de verkeerde plek. Nu krijgt de module een eigen namespace en
        zet tearDown het terug.
        """
        r = types.SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)
        self.echt = getattr(self, "echt", None) or self.mod.subprocess
        self.mod.subprocess = types.SimpleNamespace(run=lambda *a, **k: r)

    def test_a_failed_ssh_exits_instead_of_reporting_zero(self):
        self._with_ssh(255, "", "ssh: connect to host buzz-relay port 22: No route to host")
        with self.assertRaises(SystemExit):
            self.mod.subscriptions()

    def test_a_sudo_refusal_exits_instead_of_reporting_zero(self):
        self._with_ssh(1, "", "sudo: a password is required")
        with self.assertRaises(SystemExit):
            self.mod.subscriptions()

    def test_corrupt_json_exits_instead_of_reporting_zero(self):
        self._with_ssh(0, "{dit is geen json")
        with self.assertRaises(SystemExit):
            self.mod.subscriptions()

    def test_an_empty_list_really_is_zero_subscribers(self):
        self._with_ssh(0, "[]")
        self.assertEqual(self.mod.subscriptions(), [])

    def test_a_real_list_comes_through_unchanged(self):
        self._with_ssh(0, json.dumps([SUB]))
        self.assertEqual(self.mod.subscriptions(), [SUB])
