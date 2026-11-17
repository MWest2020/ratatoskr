# SPDX-License-Identifier: MIT
"""What one project shows on westerweel.work/nu/ (status_strip, status_public).

The strings below are real roadmap items from the page of 2026-11-17, the day
Mark said it exposed too much."""
import json
import unittest

import status_public
import status_roadmap
from status_strip import headline, mask_clients, plain

CFG = {"projects": {"wordsworth": {}, "convergence": {"private": True}, "jarvis": {"show_private": False},
                    "draupnir": {"show_private": True}},
       "clients": [{"name": "Gooise Meren", "en": "a Dutch municipality", "nl": "een gemeente"}],
       "show_client_names": False}


class Strip(unittest.TestCase):
    def test_issue_and_pr_numbers_go(self):
        self.assertEqual(
            headline("No untokenised names left (names with particles like ter, van der): the reprocess "
                     "with a count-only check is built (#449) and deployed (homelab#58); the run is next"),
            "No untokenised names left (names with particles like ter, van der)")
        self.assertEqual(
            headline("Readable topics and search that shows the matching passage (built in #433 and #432, in "
                     "production since 2026-11-14 with homelab#58; label quality judged at the rehearsal)"),
            "Readable topics and search that shows the matching passage")
        self.assertEqual(plain("see MWest2020/wordsworth#12 and #439/#440 for it"), "see and for it")

    def test_waits_on_mark_and_mark_decided_go(self):
        self.assertEqual(
            headline("Share from the console with layered anonymisation: proposals #439/#440 merged; Mark "
                     "decided the design (#416, 2026-11-14) and the share deploy also waits on Mark: #487"),
            "Share from the console with layered anonymisation")
        self.assertIsNone(headline("Change add-android-client approved by Mark: waits on Mark: #13 "
                                   "(default: built as proposed)"))
        self.assertIsNone(headline("Change add-drive-mode (the next phase) proposed (#9); approval waits on Mark"))
        self.assertEqual(headline("Agents post images to the chat (agent-image-to-chat, proposed #239): the build "
                                  "(#243) stopped at gate 1.1, which waits on Mark's step"),
                         "Agents post images to the chat")

    def test_adr_and_decision_references_go(self):
        self.assertEqual(plain("the organisation holds the keys (ADR-0008, ADR-0009)"),
                         "the organisation holds the keys")
        self.assertEqual(headline("Banking at the bonfire and a program in place of the game's key (decision 0005)"),
                         "Banking at the bonfire and a program in place of the game's key")
        self.assertEqual(plain("Keys exportable (D36)"), "Keys exportable")
        self.assertEqual(plain("in 3D, like ADR 12 said"), "in 3D, like said")

    def test_a_short_label_keeps_its_line_and_links_go(self):
        self.assertEqual(headline("Android app: a spoken round trip, recorded in the how-to"),
                         "Android app: a spoken round trip, recorded in the how-to")
        self.assertEqual(plain("read https://github.com/MWest2020/x/pull/3 first"), "read first")

    def test_clean_parentheses_and_plain_text_stay(self):
        self.assertEqual(headline("Free disk headroom on node-01 (now about 82% full)"),
                         "Free disk headroom on node-01 (now about 82% full)")
        self.assertEqual(headline("Note (a (nested) aside) stays"), "Note (a (nested) aside) stays")
        self.assertEqual(headline("Note (a (nested #4) aside) goes"), "Note (a aside) goes")

    def test_client_names_are_hidden_unless_allowed(self):
        cl = CFG["clients"]
        self.assertEqual(mask_clients("Pilot: Gooise Meren", cl, "en", False), "Pilot: a Dutch municipality")
        self.assertEqual(mask_clients("Pilot bij gooise meren", cl, "nl", False), "Pilot bij een gemeente")
        self.assertEqual(mask_clients("Pilot: Gooise Meren", cl, "en", True), "Pilot: Gooise Meren")

    def test_the_default_config_hides_clients_and_convergence(self):
        cfg = status_public.load()
        self.assertFalse(cfg["show_client_names"])
        self.assertIn("Gooise Meren", [c["name"] for c in cfg["clients"]])
        self.assertTrue(cfg["projects"]["convergence"]["private"])


class Shown(unittest.TestCase):
    def test_private_wins_and_a_private_repo_needs_an_explicit_allow(self):
        self.assertTrue(status_public.shown("wordsworth", CFG, True))
        self.assertFalse(status_public.shown("convergence", CFG, True))   # marked private
        self.assertFalse(status_public.shown("jarvis", CFG, False))       # private repo, not allowed
        self.assertTrue(status_public.shown("draupnir", CFG, False))      # private repo, allowed
        self.assertFalse(status_public.shown("unlisted", CFG, False))     # unknown and private
        self.assertTrue(status_public.shown("unlisted", CFG, True))       # unknown and public


ROADMAP = {
    "project": "wordsworth", "goal": "A privacy-safe corpus (ADR-0008)", "current": "pilot",
    "phases": [{"id": "poc", "name": "PoC"}, {"id": "pilot", "name": "Pilot: Gooise Meren"},
               {"id": "prod", "name": "Production"}],
    "done_means": [{"item": "Report filled", "status": "done", "evidence": "https://x/1"},
                   {"item": "Every PDF redacted (#259)", "status": "open", "evidence": "https://x/2"},
                   {"item": "Go-live waits on Mark: #12", "status": "open", "evidence": "https://x/3"}],
}


class Row(unittest.TestCase):
    def row(self, doc=ROADMAP, cfg=CFG):
        return status_public.row("wordsworth", doc, cfg, True, "https://github.com/MWest2020/wordsworth")

    def test_english_from_the_roadmap_without_notes_or_client(self):
        en = self.row()["en"]
        self.assertEqual(en, {"goal": "A privacy-safe corpus", "phase": "Pilot: a Dutch municipality",
                              "next": ["Every PDF redacted"], "note": None})
        self.assertEqual(self.row()["progress"], {"done": 1, "total": 3})

    def test_dutch_without_an_nl_block_is_a_dutch_template_not_english(self):
        nl = self.row()["nl"]
        self.assertEqual(nl, {"goal": None, "phase": None, "next": [],
                              "note": "2 open punten in deze fase; de omschrijving volgt."})

    def test_dutch_from_the_nl_block_and_next_capped_at_four(self):
        doc = {**ROADMAP, "nl": {"goal": "Een privacyveilig corpus", "phase": "Pilot bij Gooise Meren",
                                 "next": ["a", "b", "c", "d", "e"]}}
        nl = self.row(doc)["nl"]
        self.assertEqual((nl["goal"], nl["phase"], nl["next"]), ("Een privacyveilig corpus", "Pilot bij een gemeente",
                                                                  ["a", "b", "c", "d"]))

    def test_an_explicit_next_list_wins_over_the_open_items(self):
        self.assertEqual(self.row({**ROADMAP, "next": ["Redact the PDFs", "Go live"]})["en"]["next"],
                         ["Redact the PDFs", "Go live"])

    def test_nothing_on_the_row_holds_a_coordination_note(self):
        text = json.dumps(self.row(), ensure_ascii=False)
        for bad in ("#", "Mark", "ADR", "Gooise", "https://x/"):
            self.assertNotIn(bad, text)

    def test_an_allowed_private_repo_is_named_not_linked(self):
        row = status_public.row("draupnir", ROADMAP, CFG, False, "https://github.com/MWest2020/draupnir")
        self.assertIsNone(row["url"])
        self.assertEqual(self.row()["url"], "https://github.com/MWest2020/wordsworth")

    def test_a_done_phase_says_so(self):
        doc = {**ROADMAP, "done_means": ROADMAP["done_means"][:1]}
        self.assertEqual(self.row(doc)["nl"]["note"], "Alles van deze fase is klaar.")
        self.assertEqual(self.row(doc)["en"]["note"], "Everything in this phase is done.")


class Schema(unittest.TestCase):
    def test_a_bad_nl_block_is_refused(self):
        import yaml
        base = yaml.safe_dump({**ROADMAP, "done_means": ROADMAP["done_means"][:1]})
        status_roadmap.parse(base + "nl: {goal: x, next: [a]}\n")
        for extra in ("nl: [x]\n", "nl: {title: x}\n", "nl: {next: x}\n", "next: [1, 2]\n"):
            with self.assertRaises(status_roadmap.BadRoadmap):
                status_roadmap.parse(base + extra)


if __name__ == "__main__":
    unittest.main()
