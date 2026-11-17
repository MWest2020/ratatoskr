# SPDX-License-Identifier: MIT
"""Plain lines for westerweel.work/nu/ (status_strip, then status_scrub): what
goes, what drops, what stops the page.

Most strings are real roadmap items from the page of 2026-11-17, the day Mark
said it exposed too much. The client is fictional: real client names stay out
of this public repository."""
import unittest

import status_scrub
from status_strip import COORD, headline, mask_clients, plain

CLIENTS = [{"name": "Zeedorp Oost", "aliases": ["ZeedorpOost", "Zedorp Oost", "ZO"],
            "en": "a Dutch municipality", "nl": "een gemeente"}]


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

    def test_more_reference_forms_go_or_drop_the_line(self):
        for line in ("Fix it (GH-12)", "Fix it (issue 12)", "Fix it (see issues/12)", "Fix it (D-12)",
                     "Fix it (see github.com/MWest2020/jarvis)", "Fix it (www.x.nl/foo)", "Fix it (12 Nov)",
                     "Fix it (17-11-2026)", "Fix it (Mark: wait)", "Fix it (wacht op Mark)"):
            self.assertEqual(headline(line), "Fix it", line)
        for line in ("Fix it per Mark", "Mark wants it fixed", "Mark agreed", "Mark to decide", "ask Mark",
                     "waits for Mark", "Mark's phone", "Mark besloot het", "wacht op de review",
                     "goedgekeurd op 3 nov",
                     "after Nov 12", "on 17.11.2026", "two PRs left", "voorstel ligt klaar"):
            self.assertIsNone(headline(line), line)
            self.assertTrue(COORD.search(line), line)
        for line in ("Fix see github.com/MWest2020/jarvis", "read docs/how-to/x.md", "go to www.x.nl/foo"):
            self.assertNotRegex(headline(line), r"/|\.(com|nl|md)", line)

    def test_ordinary_text_is_not_a_marker(self):
        for line in ("2 separate items", "version 1.8.0", "a 3D client", "node-01 about 82% full",
                     "Een dagelijkse mail met de open besluiten en de knelpunten", "the market"):
            self.assertFalse(COORD.search(line), line)

    def test_client_names_are_hidden_unless_allowed(self):
        cl = CLIENTS
        self.assertEqual(mask_clients("Pilot: Zeedorp Oost", cl, "en", False), "Pilot: a Dutch municipality")
        self.assertEqual(mask_clients("Pilot bij zeedorp oost", cl, "nl", False), "Pilot bij een gemeente")
        self.assertEqual(mask_clients("Pilot: Zeedorp Oost", cl, "en", True), "Pilot: Zeedorp Oost")

    def test_client_phrases_spellings_and_aliases_are_masked_whole(self):
        cl = CLIENTS
        cases = {("Pilot bij Gemeente Zeedorp Oost", "nl"): "Pilot bij een gemeente",
                 ("Gemeente Zeedorp Oost doet mee", "nl"): "Een gemeente doet mee",
                 ("pilot with the municipality of Zeedorp Oost", "en"): "pilot with a Dutch municipality",
                 ("Pilot: Zeedorp-Oost", "en"): "Pilot: a Dutch municipality",
                 ("Pilot: ZeedorpOost", "en"): "Pilot: a Dutch municipality",
                 ("Pilot: Zedorp Oost", "en"): "Pilot: a Dutch municipality",
                 ("ZO pilot", "en"): "A Dutch municipality pilot"}
        for (text, lang), want in cases.items():
            self.assertEqual(mask_clients(text, cl, lang, False), want, text)


class Scrub(unittest.TestCase):
    def test_a_secret_stops_everything(self):
        for s in ("key sk-ant-api03-abcdefghijkl", "tskey-api-kqeP94eRLy11CNTRL",
                  "ghp_" + "a" * 36, "cfat_" + "b" * 30, "password: hunter2"):
            with self.assertRaises(status_scrub.Leak):
                status_scrub.clean_tree({"projects": [{"title": s}]})

    def test_emails_and_ids_are_stripped(self):
        out = status_scrub.clean("mail mark@westerweel.work about 6e01a86a-4c86-4a2c-a526-0fe76c374d52")
        self.assertNotIn("@", out)
        self.assertNotIn("6e01a86a", out)

    def test_a_private_repo_is_named_not_linked(self):
        self.assertIsNone(status_scrub.public_url("https://github.com/x/y", False))
        self.assertEqual(status_scrub.public_url("https://github.com/x/y", True), "https://github.com/x/y")


if __name__ == "__main__":
    unittest.main()
