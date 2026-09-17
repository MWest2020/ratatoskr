#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""De docs-drift-gate, lokaal.

Waarom dit bestaat: de README van deze repo heette op 2026-09-15 nog "Boomhuis",
noemde zes chat-agents terwijl er acht draaiden, en verwees naar units
`boomhuis-chat`/`boomhuis-agents` die al `ratatoskr-*` heetten. De workflow
docs-gates bestond al in de hub en draait op elke PR — maar deze repo had hem
nooit aangezet, én er wordt rechtstreeks naar main gepusht, waar geen PR aan te
pas komt.

De gate mag niet stil uitvallen. Vandaar de test op de foutgevallen: een
workflow zonder `code_paths` hoort hard te stoppen, niet groen te worden.
"""
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docs_drift  # noqa: E402


class TestRaakt(unittest.TestCase):
    def test_map_prefix(self):
        self.assertTrue(docs_drift.raakt("chat/app.js", ["chat/"]))
        self.assertTrue(docs_drift.raakt("chat/e2e/x.js", ["chat/"]))
        self.assertFalse(docs_drift.raakt("chatbot.md", ["chat/"]))

    def test_glob(self):
        self.assertTrue(docs_drift.raakt("scripts/x.py", ["scripts/*.py"]))
        self.assertFalse(docs_drift.raakt("scripts/x.sh", ["scripts/*.py"]))


class TestCodePaths(unittest.TestCase):
    def test_leest_de_echte_workflow(self):
        paden = docs_drift.code_paths()
        self.assertIn("chat/", paden)
        self.assertIn("agents/", paden)

    def test_een_workflow_zonder_code_paths_stopt_hard(self):
        """Stil terugvallen op niets zou de gate onzichtbaar uitzetten."""
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write("name: docs-gates\non: [pull_request]\n")
            pad = f.name
        self.addCleanup(os.unlink, pad)
        with self.assertRaises(SystemExit):
            docs_drift.code_paths(pad)


class TestMain(unittest.TestCase):
    def _draai(self, paden, env=None):
        # stdout opvangen: de gate hóórt te praten, maar niet dwars door de
        # uitvoer van verify.sh heen.
        oud_in, oud_uit, oud_env = sys.stdin, sys.stdout, dict(os.environ)
        sys.stdin = io.StringIO("\n".join(paden))
        sys.stdout = io.StringIO()
        os.environ.pop("DOCS_DRIFT_OK", None)
        os.environ.update(env or {})
        try:
            return docs_drift.main()
        finally:
            sys.stdin, sys.stdout = oud_in, oud_uit
            os.environ.clear()
            os.environ.update(oud_env)

    def test_code_zonder_docs_weigert(self):
        self.assertEqual(self._draai(["chat/app.js"]), 1)

    def test_code_met_docs_mag_door(self):
        self.assertEqual(self._draai(["chat/app.js", "docs/how-to/x.md"]), 0)

    def test_readme_telt_NIET_als_docs(self):
        """De hub telt alleen docs/. Deze spiegel telde README.md er eerst ook
        bij — lokaal groen, in CI rood, op 2026-09-16 op PR #139. Eén afspraak
        met twee handhavers werd zo twee afspraken, precies de fout waar deze
        gate voor bestaat. Wil je README.md laten meetellen, dan verander je dat
        in de hub."""
        self.assertEqual(self._draai(["chat/app.js", "README.md"]), 1)

    def test_alleen_docs_mag_door(self):
        self.assertEqual(self._draai(["docs/index.md"]), 0)

    def test_niets_mag_door(self):
        self.assertEqual(self._draai([]), 0)

    def test_ontsnappingsluik_is_zichtbaar_maar_werkt(self):
        self.assertEqual(self._draai(["chat/app.js"], {"DOCS_DRIFT_OK": "1"}), 0)


if __name__ == "__main__":
    unittest.main()
