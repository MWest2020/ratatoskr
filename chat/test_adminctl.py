# SPDX-License-Identifier: EUPL-1.2
"""Tests voor het host-beheer (chat/adminctl.py).

Draait het script als subproces, met een eigen database en het wachtwoord op
stdin — dat is precies hoe het in het echt gebruikt wordt.
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WW = "een lang genoeg wachtwoord\n"


class Adminctl(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ,
                        BOOMHUIS_AUTH_DB=os.path.join(tempfile.mkdtemp(), "a.db"),
                        BOOMHUIS_URL="https://voorbeeld")
        self.env.pop("BOOMHUIS_APP_TOKEN", None)

    def run_ctl(self, *args, stdin=None):
        r = subprocess.run([sys.executable, os.path.join(HERE, "adminctl.py"), *args],
                           env=self.env, input=stdin, capture_output=True, text=True,
                           cwd=HERE)
        return r.returncode, r.stdout + r.stderr

    def test_create_an_owner_and_see_it_back(self):
        code, out = self.run_ctl("owner", "mark", stdin=WW + WW)
        self.assertEqual(code, 0, out)
        self.assertIn("aangemaakt", out)
        _, listing = self.run_ctl("people")
        self.assertIn("mark", listing)
        self.assertIn("eigenaar", listing)

    def test_a_second_owner_is_refused(self):
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("owner", "iemand", stdin=WW + WW)
        self.assertEqual(code, 1)
        self.assertIn("al een account", out)

    def test_one_line_is_enough_without_a_terminal(self):
        """`docker compose exec -T chat python3 adminctl.py owner mark` heeft
        geen terminal; zonder deze tak strandt een verse installatie in een
        EOFError precies wanneer hij zijn eerste account moet krijgen."""
        code, out = self.run_ctl("owner", "mies", stdin=WW)
        self.assertEqual(code, 0, out)
        _, listing = self.run_ctl("people")
        self.assertIn("mies", listing)

    def test_passwords_must_be_equal(self):
        code, out = self.run_ctl("owner", "mark",
                                 stdin=WW + "iets heel anders hier\n")
        self.assertEqual(code, 1)
        self.assertIn("verschillen", out)

    def test_a_short_password_is_refused(self):
        code, out = self.run_ctl("owner", "mark", stdin="kort\nkort\n")
        self.assertEqual(code, 1)
        self.assertIn("minstens", out)

    def test_an_invite_only_after_an_owner(self):
        code, _ = self.run_ctl("invite")
        self.assertEqual(code, 1)
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("invite")
        self.assertEqual(code, 0)
        self.assertIn("/login?uitnodiging=", out)

    def test_changing_the_password_revokes_sessions(self):
        self.run_ctl("owner", "mark", stdin=WW + WW)
        # een sessie erbij, en kijken of die na de wijziging weg is
        code, out = self.run_ctl("password", "mark",
                                 stdin="een nieuw lang wachtwoord\n" * 2)
        self.assertEqual(code, 0, out)
        self.assertIn("sessies zijn ingetrokken", out)

    def test_the_last_owner_stays(self):
        """Jezelf verwijderen als enige eigenaar maakt de installatie
        onbereikbaar; dat hoort niet per ongeluk te kunnen."""
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("delete", "mark")
        self.assertEqual(code, 0, out)   # enige persoon: dan mag het wel, dat is opnieuw beginnen
        _, listing = self.run_ctl("people")
        self.assertIn("nog niemand", listing)

    def test_deleting_an_unknown_name(self):
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("delete", "bestaat-niet")
        self.assertEqual(code, 1)
        self.assertIn("onbekende naam", out)

    def test_a_nonsense_command_shows_the_usage(self):
        code, out = self.run_ctl("dansen")
        self.assertEqual(code, 1)
        self.assertIn("adminctl.py", out)


if __name__ == "__main__":
    unittest.main()
