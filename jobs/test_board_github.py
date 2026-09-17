# SPDX-License-Identifier: MIT
"""Tests voor de GitHub-kant van het bord: PR's en issues.

Een eigen bestand omdat `test_board` over de 200-regelgrens ging, en omdat deze
tests over een andere bron gaan dan de schijfkant (OpenSpec-changes, sessies).
Die twee raken elkaar alleen in het bord zelf.

Draaien met: cd jobs && python3 -m unittest test_board_github
"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board  # noqa: E402
import board_github  # noqa: E402

COLUMNS = [{"key": "proposal", "title": "voorstel", "stale_days": 14},
           {"key": "building", "title": "bouwen", "stale_days": 3},
           {"key": "review", "title": "review", "stale_days": 2},
           {"key": "merged", "title": "gemerged", "stale_days": 0},
           {"key": "backlog", "title": "backlog", "stale_days": 30}]


class Issues(unittest.TestCase):
    """Open issues horen op het bord: het werk dat nog geen voorstel is. Zonder
    die bron stond de helft van de afspraak -- klein = issue, epic = spec --
    buiten beeld."""

    #: Alles wat deze klasse vervangt gaat hier weer terug. unittest draait de
    #: klassen op alfabet, dus Issues komt vóór Snapshot: een patch die blijft
    #: staan laat de PR-tests vallen op een fout die niet van hen is.
    GEPATCHT = ("issue_rows", "open_prs", "merged_prs", "gh_json")

    def setUp(self):
        self._echt = {n: getattr(board_github, n) for n in self.GEPATCHT}

    def tearDown(self):
        for n, f in self._echt.items():
            setattr(board_github, n, f)

    ROWS = [{"repository": {"name": "wordsworth"}, "number": 78,
             "title": "Zoeken binnen een dossier", "url": "u",
             "updatedAt": "2026-09-17T18:00:00Z",
             "labels": [{"name": "spec-nodig"}, {"name": "mvp"}]},
            {"repository": {"name": "wordsworth"}, "number": 77,
             "title": "Documentnamen", "url": "u2",
             "updatedAt": "2026-09-17T18:00:00Z",
             "labels": [{"name": "direct"}, {"name": "ux"}]},
            {"repository": {"name": "oud-project"}, "number": 1, "title": "x",
             "url": "u3", "updatedAt": "2026-09-17T18:00:00Z", "labels": []}]

    def test_an_issue_lands_in_backlog_with_its_mark(self):
        cards = board_github.issues_to_cards(self.ROWS, time.time())
        self.assertTrue(all(c["column"] == "backlog" for c in cards))
        self.assertIn("[spec-nodig]", cards[0]["title"])
        self.assertIn("[direct]", cards[1]["title"])

    def test_an_issue_without_a_mark_keeps_its_plain_title(self):
        """Niet elk issue is ingedeeld, en een verzonnen label is erger dan geen."""
        cards = board_github.issues_to_cards(self.ROWS, time.time())
        self.assertEqual(cards[2]["title"], "#1 x")

    def test_an_ignored_repo_is_dropped_here_too(self):
        cards = board_github.issues_to_cards(self.ROWS, time.time(), {"oud-project"})
        self.assertEqual([c["repo"] for c in cards], ["wordsworth", "wordsworth"])

    def test_a_read_error_is_an_error_and_not_an_empty_board(self):
        """'Ik weet het niet' en 'er is niets' zijn verschillende antwoorden."""
        def boom(owner):
            raise RuntimeError("gh weg")
        board_github.issue_rows = boom
        board.board_github.open_prs = lambda owner: []
        board.board_github.merged_prs = lambda *a: []
        with tempfile.TemporaryDirectory() as d:
            cfg = {"columns": COLUMNS,
                   "sources": {"openspec_glob": "/does/not/exist/*/proposal.md",
                               "github_owner": "owner", "session_runs": "/nope",
                               "pr_cache": os.path.join(d, "prs.json"),
                               "issue_cache": os.path.join(d, "issues.json")}}
            snap = board.build(cfg, now=time.time())
        self.assertTrue(any("issues not fetched" in e for e in snap["errors"]),
                        snap["errors"])

    def test_issues_come_from_the_cache_so_the_board_stays_cheap(self):
        """Het bord draait elke twee minuten; een ongecachte issue-query zou dat
        elke keer een GitHub-aanroep kosten."""
        gevraagd = []
        board_github.issue_rows = lambda owner: gevraagd.append(owner) or self.ROWS
        with tempfile.TemporaryDirectory() as d:
            pad = os.path.join(d, "issues.json")
            now = time.time()
            for _ in range(3):
                board._cached(pad, now, 600, "issues",
                              lambda: board_github.issue_rows("owner"))
        self.assertEqual(len(gevraagd), 1, gevraagd)


class Ignore(unittest.TestCase):
    def test_ignored_repo_is_dropped(self):
        """A PR on a repo you no longer work on is the oldest card, and therefore
        shouts loudest every day. Not every open thing is work."""
        rows = [{"repository": {"name": "oud-project"}, "number": 1, "title": "x",
                 "updatedAt": "2026-01-01T00:00:00Z", "url": "", "isDraft": False,
                 "author": {"login": "a"}}]
        board_github.gh_json = lambda args: rows if "--state=open" in args else []
        self.assertEqual(board_github.pr_cards("owner", 3, time.time(), {"oud-project"}), [])
        self.assertEqual(len(board_github.pr_cards("owner", 3, time.time(), set())), 1)
