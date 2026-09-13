# SPDX-License-Identifier: EUPL-1.2
"""De naad tussen de drie stukken van de push-keten.

Elk stuk had zijn eigen tests en elk stuk was groen. De keten was het niet, en
alle drie de storingen van 11-13 september zaten precies in de overgang:

1. De chat schreef de abonnementen naar het volume, de helper las het OUDE pad.
   Uitkomst: "0 abonnees", terwijl er een abonnee was.
2. `prune` schreef het bestand opnieuw als root 0600. Uitkomst: de chat (uid
   10001) kon het daarna niet meer lezen en er ook geen nieuw abonnement meer in
   opslaan — en niets zei dat.
3. Een leesfout mocht nooit als "0 abonnees" doorgaan, want dan meldt de
   verzender succes terwijl er niemand bereikt is.

Geen van die drie is met een unittest per bestand te vangen: ze bestaan alleen
in de overgang. Vandaar deze suite, die de ECHTE chat-module, het ECHTE
helper-script en de ECHTE verzender-parser achter elkaar zet.
"""
import importlib
import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HELPER = os.path.join(HERE, "vm", "boomhuis-push-subs")


def _load(name, path):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _chat_push(subs_path):
    """De chat-module zoals de HTTP-route hem gebruikt, wijzend naar `subs_path`."""
    sys.path.insert(0, os.path.join(REPO, "chat"))
    os.environ["PUSH_SUBS_PATH"] = subs_path
    try:
        import push
        return importlib.reload(push)
    finally:
        sys.path.pop(0)


def _helper(subs_path):
    """Het echte VM-script, met zijn padlijst op onze tijdelijke map gezet."""
    mod = _load("push_subs_helper_chain", HELPER)
    mod.PATHS = [subs_path]
    return mod


SUB = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc",
       "keys": {"p256dh": "p" * 20, "auth": "a" * 16}}
SUB2 = {"endpoint": "https://fcm.googleapis.com/fcm/send/def",
        "keys": {"p256dh": "q" * 20, "auth": "b" * 16}}


class WhatTheChatWritesTheHelperReads(unittest.TestCase):
    """Storing 1: twee bestanden, twee waarheden, nul signalen."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "push_subs.json")

    def tearDown(self):
        os.environ.pop("PUSH_SUBS_PATH", None)

    def test_a_subscription_stored_by_the_chat_comes_back_from_the_helper(self):
        chat = _chat_push(self.path)
        self.assertTrue(chat.add_subscription(SUB))
        helper = _helper(self.path)
        self.assertEqual(helper._read(), [SUB])

    def test_the_helper_reads_the_path_the_chat_actually_wrote(self):
        # Niet "een pad", maar HET pad. Dit is de assertie die de migratie van
        # 11 september had laten vallen.
        chat = _chat_push(self.path)
        chat.add_subscription(SUB)
        self.assertTrue(os.path.exists(self.path), "de chat schreef ergens anders")
        helper = _helper(self.path)
        self.assertEqual(helper._path(), self.path)


class PruningLeavesTheFileUsableForTheChat(unittest.TestCase):
    """Storing 2: de helper draait als root, het bestand hoort bij de chat."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "push_subs.json")

    def tearDown(self):
        os.environ.pop("PUSH_SUBS_PATH", None)

    def test_after_a_prune_the_chat_can_still_read_and_add(self):
        chat = _chat_push(self.path)
        chat.add_subscription(SUB)
        chat.add_subscription(SUB2)

        helper = _helper(self.path)
        keep = [s for s in helper._read() if s["endpoint"] != SUB["endpoint"]]
        helper._write(keep)

        # Dit is de hele storing in één regel: ná de prune moest de chat nog
        # kunnen lezen EN schrijven. Dat kon hij niet, en er stond nergens iets.
        chat = _chat_push(self.path)
        self.assertEqual([s["endpoint"] for s in chat.load_subscriptions()], [SUB2["endpoint"]])
        self.assertTrue(chat.add_subscription(SUB))
        self.assertEqual(len(chat.load_subscriptions()), 2)

    def test_a_prune_keeps_owner_and_mode(self):
        chat = _chat_push(self.path)
        chat.add_subscription(SUB)
        voor = os.stat(self.path)
        helper = _helper(self.path)
        helper._write(helper._read())
        na = os.stat(self.path)
        self.assertEqual((na.st_uid, na.st_gid), (voor.st_uid, voor.st_gid))
        self.assertEqual(stat.S_IMODE(na.st_mode), stat.S_IMODE(voor.st_mode))


class TheHelperRunsAsACommand(unittest.TestCase):
    """De verzender roept het script aan als commando, niet als module. Als dat
    aanroeppad stuk is, helpt geen enkele geïmporteerde functie."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "push_subs.json")

    def tearDown(self):
        os.environ.pop("PUSH_SUBS_PATH", None)

    def _run(self, cmd, stdin=None):
        # Zelfde vorm als de sudoers-regel: het script als uitvoerbaar bestand.
        script = f"""
import importlib.machinery, importlib.util, sys
spec = importlib.util.spec_from_loader("h", importlib.machinery.SourceFileLoader("h", {HELPER!r}))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.PATHS = [{self.path!r}]
sys.argv = ["boomhuis-push-subs", {cmd!r}]
m.main()
"""
        return subprocess.run([sys.executable, "-c", script], input=stdin,
                              capture_output=True, text=True)

    def test_read_prints_json_the_sender_can_parse(self):
        chat = _chat_push(self.path)
        chat.add_subscription(SUB)
        r = self._run("read")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [SUB])

    def test_no_file_is_an_empty_list_and_not_an_error(self):
        r = self._run("read")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [])

    def test_an_unknown_command_fails_instead_of_doing_something(self):
        r = self._run("delete-everything")
        self.assertNotEqual(r.returncode, 0)


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


if __name__ == "__main__":
    unittest.main()
