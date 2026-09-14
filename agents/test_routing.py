# SPDX-License-Identifier: EUPL-1.2
"""Doorsturen: wat er mag, en vooral wat er niet mag.

De veiligheidsclaim van deze versie is anders dan die van de eerste. Die
controleerde of een KOPIE klopte; deze maakt kopiëren overbodig — de listener
haalt de inhoud zelf uit het kanaal, de agent wijst alleen aan. Een agent kan
dus geen citaat verzinnen, en dat is sterker dan een woordelijkheidscontrole.
"""
import unittest

import routing

KANALEN = {"bouw": "cid-bouw", "general": "cid-general", "escalatie": "cid-esc"}
CFG = {"routes": ["bouw"], "nsec": "n", "npub": "p"}
NAMEN = {"pk-mark": "mark", "pk-odin": "odin"}
BERICHTEN = [
    {"id": "aaaa1111bbbb2222", "pubkey": "pk-mark", "content": "F1 t/m F4 zijn al gefixt"},
    {"id": "cccc3333dddd4444", "pubkey": "pk-odin", "content": "regel een\nregel twee"},
    {"id": "aaaa9999eeee8888", "pubkey": "pk-mark", "content": "iets anders"},
]


class DeMarker(unittest.TestCase):
    def test_kanaal_id_en_notitie(self):
        self.assertEqual(
            routing.read_marker("!forward #bouw aaaa1111\nkijk hiernaar"),
            ("bouw", "aaaa1111", "kijk hiernaar"))

    def test_zonder_notitie_mag_ook(self):
        self.assertEqual(routing.read_marker("!forward bouw aaaa1111"),
                         ("bouw", "aaaa1111", ""))

    def test_route_blijft_werken_als_alias(self):
        # Een agent die de oude vorm geleerd heeft mag niet stil falen omdat ik
        # het woord veranderd heb.
        self.assertEqual(routing.read_marker("!route #bouw aaaa1111")[0], "bouw")

    def test_geen_marker_is_none(self):
        self.assertIsNone(routing.read_marker("gewoon een antwoord"))

    def test_strippen_haalt_marker_en_notitie_weg(self):
        ans = "Ik stuur het door.\n\n!forward #bouw aaaa1111\nmet duiding"
        self.assertEqual(routing.strip_marker(ans), "Ik stuur het door.")


class HetAanwijzen(unittest.TestCase):
    def test_een_voorvoegsel_volstaat(self):
        b = routing.find_message(BERICHTEN, "aaaa1111")
        self.assertEqual(b["content"], "F1 t/m F4 zijn al gefixt")

    def test_dubbelzinnig_voorvoegsel_wijst_niets_aan(self):
        # "aaaa" past op twee berichten: dat is geen aanwijzing maar een gok.
        self.assertIsNone(routing.find_message(BERICHTEN, "aaaa"))

    def test_onbekend_id_geeft_none(self):
        self.assertIsNone(routing.find_message(BERICHTEN, "ffff0000"))


class HetMandaat(unittest.TestCase):
    def test_een_kanaal_in_het_mandaat_mag(self):
        ok, reden = routing.may_forward(CFG, "bouw", KANALEN)
        self.assertTrue(ok, reden)

    def test_een_kanaal_erbuiten_mag_niet(self):
        ok, reden = routing.may_forward(CFG, "general", KANALEN)
        self.assertFalse(ok)
        self.assertIn("mandaat", reden)

    def test_zonder_routes_mag_niets(self):
        ok, reden = routing.may_forward({}, "bouw", KANALEN)
        self.assertFalse(ok)
        self.assertIn("geen routes", reden)

    def test_verkeerd_type_geeft_geen_rechten(self):
        for kapot in ({"routes": "bouw"}, {"routes": True}, {"routes": {"bouw": 1}}):
            self.assertEqual(routing.allowed_channels(kapot), [], kapot)


class WatErLandt(unittest.TestCase):
    def test_de_bron_staat_erbij(self):
        t = routing.forwarded_text("mark", "architectuur", BERICHTEN[0], "odin", "")
        self.assertIn("#architectuur", t)
        self.assertIn("mark", t)
        self.assertIn("aaaa1111bbbb", t)

    def test_de_inhoud_staat_in_een_blockquote(self):
        t = routing.forwarded_text("odin", "general", BERICHTEN[1], "odin", "")
        self.assertIn("> regel een", t)
        self.assertIn("> regel twee", t)

    def test_de_eigen_notitie_draagt_de_naam_van_de_doorstuurder(self):
        # Zonder die naam kan de ontvanger de duiding voor het origineel
        # aanzien, en dat is precies wat doorsturen moet voorkomen.
        t = routing.forwarded_text("mark", "general", BERICHTEN[0], "odin", "dit is urgent")
        self.assertIn("**odin** erbij: dit is urgent", t)


class Uitvoeren(unittest.TestCase):
    def setUp(self):
        self.verstuurd = []

    def _handle(self, answer, cfg=None, berichten=None):
        cfg = cfg or CFG

        def send(cid, tekst, nsec, npub):
            self.verstuurd.append((cid, tekst, nsec))
            return True

        return routing.handle(answer, "odin", cfg, "architectuur",
                              BERICHTEN if berichten is None else berichten,
                              NAMEN, KANALEN, send, "cid-hier")

    def test_een_goede_doorstuur_post_en_laat_het_antwoord_schoon(self):
        rest = self._handle("Doe ik.\n\n!forward #bouw aaaa1111\nzie punt 3")
        self.assertEqual(rest, "Doe ik.")
        self.assertEqual(len(self.verstuurd), 1)
        cid, tekst, nsec = self.verstuurd[0]
        self.assertEqual(cid, "cid-bouw")
        self.assertIn("> F1 t/m F4 zijn al gefixt", tekst)
        self.assertIn("**odin** erbij: zie punt 3", tekst)
        # De handtekening is die van de DOORSTUURDER, niet van de schrijver.
        self.assertEqual(nsec, "n")

    def test_een_verboden_kanaal_stuurt_niets_en_meldt_het(self):
        rest = self._handle("!forward #general aaaa1111")
        self.assertEqual([v[0] for v in self.verstuurd], ["cid-esc"])
        self.assertIn("mandaat", self.verstuurd[0][1])
        self.assertIn("geweigerd", rest)

    def test_een_verzonnen_id_stuurt_niets(self):
        # De agent kan geen citaat verzinnen: hij wijst aan, de listener kopieert.
        rest = self._handle("!forward #bouw ffff0000\nvertrouw me")
        self.assertEqual([v[0] for v in self.verstuurd], ["cid-esc"])
        self.assertIn("geen eenduidig bericht", self.verstuurd[0][1])
        self.assertIn("geweigerd", rest)

    def test_zonder_marker_blijft_het_antwoord_ongemoeid(self):
        self.assertEqual(self._handle("gewoon antwoord"), "gewoon antwoord")
        self.assertEqual(self.verstuurd, [])


if __name__ == "__main__":
    unittest.main()
