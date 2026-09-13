# SPDX-License-Identifier: EUPL-1.2
"""Sleutelopslag: waar een sleutel vandaan komt, en wanneer hij niet telt.

De twee tests die ertoe doen zijn de weigeringen. Een ontbrekende sleutel en een
te ruim leesbare sleutel moeten allebei een reden opleveren en geen sleutel —
stil doorgaan met "dan maar zonder" is hoe een installatie half draait zonder
dat iemand weet welke helft.
"""
import os
import tempfile
import unittest

import keystore

NSEC = "nsec1" + "q" * 58
ANDERE = "nsec1" + "p" * 58


class BestandBackend(unittest.TestCase):
    def setUp(self):
        self.map_ = tempfile.mkdtemp()

    def test_wat_je_neerlegt_lees_je_terug(self):
        keystore.schrijf_bestand(self.map_, "odin", NSEC)
        self.assertEqual(keystore.lees("odin", backend="bestand", map_=self.map_), NSEC)

    def test_de_map_en_het_bestand_zijn_krap(self):
        pad = keystore.schrijf_bestand(self.map_, "odin", NSEC)
        self.assertEqual(os.stat(pad).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.map_).st_mode & 0o777, 0o700)

    def test_te_ruim_leesbaar_telt_niet(self):
        pad = keystore.schrijf_bestand(self.map_, "odin", NSEC)
        os.chmod(pad, 0o644)
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("odin", backend="bestand", map_=self.map_)
        self.assertIn("te ruim", str(e.exception))

    def test_ontbrekend_geeft_een_reden_geen_lege_sleutel(self):
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("bestaat-niet", backend="bestand", map_=self.map_)
        self.assertIn("bestaat niet", str(e.exception))

    def test_een_bestaande_sleutel_wordt_nooit_overschreven(self):
        # Overschrijven maakt elke agent die die sleutel gebruikte onbereikbaar;
        # dit is het verschil tussen idempotent en destructief.
        keystore.schrijf_bestand(self.map_, "odin", NSEC)
        with self.assertRaises(FileExistsError):
            keystore.schrijf_bestand(self.map_, "odin", ANDERE)
        self.assertEqual(keystore.lees("odin", backend="bestand", map_=self.map_), NSEC)

    def test_iets_dat_geen_nsec_is_gaat_er_niet_in(self):
        with self.assertRaises(keystore.SleutelFout):
            keystore.schrijf_bestand(self.map_, "odin", "hallo")

    def test_iets_dat_geen_nsec_is_komt_er_niet_uit(self):
        # Een half geschreven bestand levert anders een "sleutel" op waarmee de
        # relay je weigert — en dan ga je bij de relay zoeken.
        pad = os.path.join(self.map_, "odin.nsec")
        fd = os.open(pad, os.O_WRONLY | os.O_CREAT, 0o600)
        os.write(fd, b"nsec1kapot\n")
        os.close(fd)
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("odin", backend="bestand", map_=self.map_)
        self.assertIn("geldige nsec", str(e.exception))


class SopsBackend(unittest.TestCase):
    """Marks installatie moet blijven werken; de vorm van dat bestand is de
    afspraak die run.sh met awk leest."""

    def setUp(self):
        self.echt = keystore.subprocess.run

    def tearDown(self):
        keystore.subprocess.run = self.echt

    def _sops(self, stdout, rc=0):
        import types
        keystore.subprocess.run = lambda *a, **k: types.SimpleNamespace(
            returncode=rc, stdout=stdout, stderr="")

    def test_de_nsec_van_de_juiste_handle(self):
        self._sops(f"identities:\n  odin:\n    nsec: {NSEC}\n  bouwer:\n    nsec: {ANDERE}\n")
        pad = os.path.join(tempfile.mkdtemp(), "identities.yaml")
        open(pad, "w").write("x")
        self.assertEqual(keystore.lees("odin", backend="sops", sops_pad=pad), NSEC)
        self.assertEqual(keystore.lees("bouwer", backend="sops", sops_pad=pad), ANDERE)

    def test_een_mislukte_decrypt_is_een_fout_geen_lege_sleutel(self):
        self._sops("", rc=1)
        pad = os.path.join(tempfile.mkdtemp(), "identities.yaml")
        open(pad, "w").write("x")
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("odin", backend="sops", sops_pad=pad)
        self.assertIn("sops-decrypt faalde", str(e.exception))

    def test_een_ontbrekend_bestand_zegt_dat(self):
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("odin", backend="sops", sops_pad="/bestaat/niet.yaml")
        self.assertIn("bestaat niet", str(e.exception))


class DeKeuze(unittest.TestCase):
    def test_onbekende_backend_noemt_de_opties(self):
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("odin", backend="magie")
        self.assertIn("sops, bestand", str(e.exception))

    def test_default_is_sops_zodat_marks_installatie_niet_verandert(self):
        os.environ.pop("RATATOSKR_KEYSTORE", None)
        with self.assertRaises(keystore.SleutelFout) as e:
            keystore.lees("odin", sops_pad="/bestaat/niet.yaml")
        self.assertIn("bestaat niet", str(e.exception))


if __name__ == "__main__":
    unittest.main()
