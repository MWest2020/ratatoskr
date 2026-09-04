# SPDX-License-Identifier: EUPL-1.2
"""Offline tests voor het schrijf-token (chat/auth.py).

Draaien vanuit chat/: `python3 -m unittest test_auth`. Geen relay of netwerk
nodig — auth.py is puur env + header-vergelijking.
"""
import os
import unittest

import auth


class _Headers(dict):
    """Minimale stand-in voor http.client.HTTPMessage: .get() volstaat."""


def _hdr(token=None):
    return _Headers({} if token is None else {auth.HEADER: token})


class WriteAllowed(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("BOOMHUIS_APP_TOKEN")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("BOOMHUIS_APP_TOKEN", None)
        else:
            os.environ["BOOMHUIS_APP_TOKEN"] = self._old

    def _set(self, value):
        if value is None:
            os.environ.pop("BOOMHUIS_APP_TOKEN", None)
        else:
            os.environ["BOOMHUIS_APP_TOKEN"] = value

    def test_zonder_ingesteld_token_mag_alles(self):
        # Niet-ingesteld en leeg/spaties zijn hetzelfde: uit.
        for value in (None, "", "   "):
            self._set(value)
            self.assertTrue(auth.write_allowed(_hdr()))
            self.assertTrue(auth.write_allowed(_hdr("wat dan ook")))

    def test_met_ingesteld_token_alleen_het_juiste(self):
        self._set("geheim123")
        self.assertTrue(auth.write_allowed(_hdr("geheim123")))
        self.assertFalse(auth.write_allowed(_hdr()))          # geen header
        self.assertFalse(auth.write_allowed(_hdr("")))        # lege header
        self.assertFalse(auth.write_allowed(_hdr("geheim12")))  # prefix
        self.assertFalse(auth.write_allowed(_hdr("geheim1234")))  # langer
        self.assertFalse(auth.write_allowed(_hdr("Geheim123")))   # hoofdletter

    def test_spaties_rond_het_ingestelde_token_tellen_niet_mee(self):
        # chat.env kan een spatie of newline meegeven; dat mag niet stil een
        # ander token opleveren dan wat Mark invoert.
        self._set("  geheim123\n")
        self.assertTrue(auth.write_allowed(_hdr("geheim123")))
        self.assertEqual(auth.required_token(), "geheim123")


if __name__ == "__main__":
    unittest.main()
