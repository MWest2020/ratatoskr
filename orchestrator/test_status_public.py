# SPDX-License-Identifier: MIT
"""Which projects reach westerweel.work/nu/ and what one project shows there
(status_public). The client is fictional: real client names stay out of this
public repository. The text rules themselves: test_status_strip.py."""
import json
import os
import tempfile
import unittest
from unittest import mock

import yaml

import status_public
import status_roadmap

CFG = {"projects": {"wordsworth": {}, "convergence": {"private": True}, "jarvis": {"show_private": False},
                    "draupnir": {"show_private": True}},
       "clients": [{"name": "Zeedorp Oost", "aliases": ["ZeedorpOost", "Zedorp Oost", "ZO"],
                    "en": "a Dutch municipality", "nl": "een gemeente"}],
       "show_client_names": False}


class Config(unittest.TestCase):
    def test_the_default_config_hides_clients_and_convergence(self):
        cfg = status_public.load()
        self.assertFalse(cfg["show_client_names"])
        self.assertTrue(cfg["projects"]["convergence"]["private"])
        self.assertNotIn("clients", yaml_keys(status_public.CONFIG))  # the list is local, not in git

    def test_without_the_local_client_list_it_says_so(self):
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.dict(os.environ, {"STATUS_CLIENTS_FILE": os.path.join(t, "none.yml")}):
                self.assertTrue(status_public.load()["clients_missing"])
            path = os.path.join(t, "c.yml")
            with open(path, "w") as fh:
                fh.write('clients:\n  - {name: "Zeedorp Oost", en: "a town", nl: "een dorp"}\n')
            with mock.patch.dict(os.environ, {"STATUS_CLIENTS_FILE": path}):
                cfg = status_public.load()
        self.assertFalse(cfg["clients_missing"])
        self.assertEqual(cfg["clients"][0]["nl"], "een dorp")


def yaml_keys(path):
    with open(path) as fh:
        return set(yaml.safe_load(fh))


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
    "phases": [{"id": "poc", "name": "PoC"}, {"id": "pilot", "name": "Pilot: Zeedorp Oost"},
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
        doc = {**ROADMAP, "nl": {"goal": "Een privacyveilig corpus", "phase": "Pilot bij Zeedorp Oost",
                                 "next": ["a", "b", "c", "d", "e"]}}
        nl = self.row(doc)["nl"]
        self.assertEqual((nl["goal"], nl["phase"], nl["next"]), ("Een privacyveilig corpus", "Pilot bij een gemeente",
                                                                  ["a", "b", "c", "d"]))

    def test_an_explicit_next_list_wins_over_the_open_items(self):
        self.assertEqual(self.row({**ROADMAP, "next": ["Redact the PDFs", "Go live"]})["en"]["next"],
                         ["Redact the PDFs", "Go live"])

    def test_nothing_on_the_row_holds_a_coordination_note(self):
        text = json.dumps(self.row(), ensure_ascii=False)
        for bad in ("#", "Mark", "ADR", "Zeedorp", "https://x/"):
            self.assertNotIn(bad, text)

    def test_an_allowed_private_repo_is_named_not_linked(self):
        row = status_public.row("draupnir", ROADMAP, CFG, False, "https://github.com/MWest2020/draupnir")
        self.assertIsNone(row["url"])
        self.assertEqual(self.row()["url"], "https://github.com/MWest2020/wordsworth")

    def test_a_line_naming_a_left_out_project_is_dropped(self):
        doc = {**ROADMAP, "next": ["Talk to it through the jarvis voice bridge", "Redact the PDFs"]}
        row = status_public.row("wordsworth", doc, status_public.hide(CFG, ["jarvis", "convergence"]), True, "u")
        self.assertEqual(row["en"]["next"], ["Redact the PDFs"])

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
