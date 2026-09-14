# SPDX-License-Identifier: EUPL-1.2
"""open_batons(): welke handover-batons nog op iemand wachten.

Waarom dit een test heeft. Op 2026-09-12 werd een baton neergelegd zonder
frontmatter. `open_batons()` leest `status` uit die frontmatter; zonder
frontmatter is `status` leeg, dus nooit "afgehandeld", dus stond hij drie dagen
als open werk in `_live.md` — met twee lege velden: "— . Volgende:". Het werk
was toen al af. Een regel die niets zegt, zegt ook niet dát er iets mis is.

Erger nog: een baton met kapotte YAML liet `yaml.safe_load` een exception
gooien die de hele generatie van `_live.md` meenam. Eén onleesbaar bestand en
de coordinator heeft geen overzicht meer.

Beide gevallen zijn nu een melding in plaats van stilte of een storing.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live  # noqa: E402


class TestOpenBatons(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.makedirs(os.path.join(self.tmp.name, "handover"))
        self.oud = live.ROOT
        live.ROOT = self.tmp.name
        self.addCleanup(lambda: setattr(live, "ROOT", self.oud))

    def schrijf(self, naam, inhoud):
        with open(os.path.join(self.tmp.name, "handover", naam), "w") as f:
            f.write(inhoud)

    def test_afgehandelde_baton_telt_niet_meer_mee(self):
        self.schrijf("a.md", "---\nstatus: volledig afgehandeld (2026-09-14)\n"
                             "onderwerp: iets\nnext_step: geen\n---\n\ntekst\n")
        self.assertEqual(live.open_batons(), [])

    def test_open_baton_komt_met_onderwerp_en_vervolgstap(self):
        self.schrijf("b.md", "---\nstatus: open\nonderwerp: auth-review\n"
                             "next_step: F1 repareren\n---\n\ntekst\n")
        self.assertEqual(live.open_batons(),
                         [("b.md", "auth-review", "F1 repareren")])

    def test_baton_zonder_frontmatter_zegt_dat_in_plaats_van_leeg(self):
        self.schrijf("c.md", "# Baton zonder frontmatter\n\ntekst\n")
        (naam, onderwerp, volgende), = live.open_batons()
        self.assertEqual(naam, "c.md")
        self.assertIn("GEEN FRONTMATTER", onderwerp)
        self.assertTrue(volgende, "er moet een handeling in staan")

    def test_kapotte_yaml_is_een_melding_en_geen_exception(self):
        self.schrijf("d.md", "---\nnaar: @bouwer\n---\n\ntekst\n")
        (naam, onderwerp, volgende), = live.open_batons()
        self.assertEqual(naam, "d.md")
        self.assertIn("ONLEESBAAR", onderwerp)
        self.assertTrue(volgende)

    def test_een_kapotte_baton_verbergt_de_andere_niet(self):
        self.schrijf("d.md", "---\nnaar: @bouwer\n---\n\ntekst\n")
        self.schrijf("b.md", "---\nstatus: open\nonderwerp: auth-review\n"
                             "next_step: F1 repareren\n---\n\ntekst\n")
        namen = [n for n, _, _ in live.open_batons()]
        self.assertEqual(namen, ["b.md", "d.md"])


if __name__ == "__main__":
    unittest.main()
