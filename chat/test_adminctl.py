# SPDX-License-Identifier: EUPL-1.2
"""Tests for host-side administration (chat/adminctl.py).

Runs the script as a subprocess, with its own database and the password on
stdin — which is exactly how it is used for real.
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
        self.assertIn("created", out)
        _, listing = self.run_ctl("people")
        self.assertIn("mark", listing)
        self.assertIn("owner", listing)

    def test_a_second_owner_is_refused(self):
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("owner", "iemand", stdin=WW + WW)
        self.assertEqual(code, 1)
        self.assertIn("already an account", out)

    def test_one_line_is_enough_without_a_terminal(self):
        """`docker compose exec -T chat python3 adminctl.py owner mark` has no
        terminal; without this branch a fresh installation strands in an EOFError
        exactly when it has to get its first account."""
        code, out = self.run_ctl("owner", "mies", stdin=WW)
        self.assertEqual(code, 0, out)
        _, listing = self.run_ctl("people")
        self.assertIn("mies", listing)

    def test_passwords_must_be_equal(self):
        code, out = self.run_ctl("owner", "mark",
                                 stdin=WW + "iets heel anders hier\n")
        self.assertEqual(code, 1)
        self.assertIn("differ", out)

    def test_a_short_password_is_refused(self):
        code, out = self.run_ctl("owner", "mark", stdin="kort\nkort\n")
        self.assertEqual(code, 1)
        self.assertIn("at least", out)

    def test_an_invite_only_after_an_owner(self):
        code, _ = self.run_ctl("invite")
        self.assertEqual(code, 1)
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("invite")
        self.assertEqual(code, 0)
        self.assertIn("/login?uitnodiging=", out)

    def test_changing_the_password_revokes_sessions(self):
        self.run_ctl("owner", "mark", stdin=WW + WW)
        # add a session, and see whether it is gone after the change
        code, out = self.run_ctl("password", "mark",
                                 stdin="een nieuw lang wachtwoord\n" * 2)
        self.assertEqual(code, 0, out)
        self.assertIn("sessions have been revoked", out)

    def test_the_last_owner_stays(self):
        """Deleting yourself as the only owner makes the installation
        unreachable; that should not be possible by accident."""
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("delete", "mark")
        self.assertEqual(code, 0, out)   # only person: then it is allowed, that is starting over
        _, listing = self.run_ctl("people")
        self.assertIn("nobody yet", listing)

    def test_deleting_an_unknown_name(self):
        self.run_ctl("owner", "mark", stdin=WW + WW)
        code, out = self.run_ctl("delete", "bestaat-niet")
        self.assertEqual(code, 1)
        self.assertIn("unknown name", out)

    def test_a_nonsense_command_shows_the_usage(self):
        code, out = self.run_ctl("dansen")
        self.assertEqual(code, 1)
        self.assertIn("adminctl.py", out)


if __name__ == "__main__":
    unittest.main()
