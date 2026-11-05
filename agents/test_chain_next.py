# SPDX-License-Identifier: MIT
"""The chain-after-merge grammar, pure: `## Next`, `## Depends on`, `## Deploy
precondition`, read from a proposal.md as the existing proposals already
write it."""
import unittest

import chain_next


class Next(unittest.TestCase):
    def test_a_named_step(self):
        self.assertEqual(chain_next.parse("## Next\n`originals-ingest-write`\n")["next"],
                         "originals-ingest-write")

    def test_heading_case_and_spacing_variants(self):
        for heading in ("##   NEXT", "## next", "##  Next  "):
            self.assertEqual(chain_next.parse(f"{heading}\n`b`\n")["next"], "b", heading)

    def test_prose_around_the_id_is_ignored(self):
        text = "## Next\nThe next step is `the-change`, once its parents merge.\n"
        self.assertEqual(chain_next.parse(text)["next"], "the-change")

    def test_only_the_first_section_of_a_name_counts(self):
        text = "## Next\n`first`\n## Next\n`second`\n"
        self.assertEqual(chain_next.parse(text)["next"], "first")

    def test_no_next_section_names_none(self):
        p = chain_next.parse("## Why\nsome reason\n")
        self.assertIsNone(p["next"])
        self.assertFalse(p["malformed"])

    def test_a_next_section_without_an_id_is_malformed(self):
        p = chain_next.parse("## Next\nSomeone decides later.\n")
        self.assertIsNone(p["next"])
        self.assertTrue(p["malformed"])

    def test_an_id_in_a_fenced_block_under_another_heading_is_not_a_parent(self):
        text = ("## Why\nExample:\n```\n## Depends on\n`not-a-parent`\n```\n"
                "## Depends on\n`real-parent`\n")
        self.assertEqual(chain_next.parse(text)["parents"], ["real-parent"])


class DependsOn(unittest.TestCase):
    def test_two_parents(self):
        text = "## Depends on\n`a`, and `b` once both merge.\n"
        self.assertEqual(chain_next.parse(text)["parents"], ["a", "b"])

    def test_no_depends_on_is_no_parents(self):
        self.assertEqual(chain_next.parse("## Why\nx\n")["parents"], [])


class DeployPrecondition(unittest.TestCase):
    def test_the_sections_presence_is_the_precondition(self):
        self.assertTrue(chain_next.parse("## Deploy precondition\nA person restores a backup.\n")
                         ["precondition"])

    def test_absence_is_no_precondition(self):
        self.assertFalse(chain_next.parse("## Why\nx\n")["precondition"])


if __name__ == "__main__":
    unittest.main()
