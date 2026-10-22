# SPDX-License-Identifier: MIT
"""The seam between the handbook's markdown and the listener: which heading
holds the system prompt. From 2026-09-22 to 2026-10-22 every chat agent ran with
an empty system prompt, because the handbook's English translation wrote
`## Chat facet` where this parser only knew `## Chat-facet`. Offline: the
definitions below copy the real handbook layout."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import bootstrap

FRONT = """---
status: actief
agent:
  naam: bouwer
  npub: npub1x
  chat:
    model: sonnet
    channels: [bouw]
    tools: { allow: [Read, Grep, Glob], deny: [Write, Edit, Bash] }
    skills: []
---

# bouwer

## Mandate

The bouwer makes construction concrete.

"""

# The layout of handbook docs/agents/bouwer.md after the translation (#24, #25):
# a space in the heading, a channel note after it, and a prose line before the
# blockquote that must not end up in the prompt.
ENGLISH = FRONT + """## Chat facet (ratatoskr · #bouw)

System prompt for the `claude -p` listener:

> You are 'bouwer', the build agent.
> Short, English, practical.

Channel scope: `#bouw`.

## Execution facet (habitat · builder)

> Not a chat prompt.
"""


class ChatFacet(unittest.TestCase):
    def test_the_english_heading_gives_the_prompt(self):
        d = bootstrap.parse_def(ENGLISH)
        self.assertEqual(d["system"], "You are 'bouwer', the build agent.\n"
                                      "Short, English, practical.")

    def test_the_old_hyphenated_heading_still_works(self):
        d = bootstrap.parse_def(ENGLISH.replace("## Chat facet", "## Chat-facet"))
        self.assertTrue(d["system"].startswith("You are 'bouwer'"))

    def test_the_next_section_is_not_swallowed(self):
        self.assertNotIn("Not a chat prompt", bootstrap.parse_def(ENGLISH)["system"])

    def test_no_heading_means_no_prompt(self):
        d = bootstrap.parse_def(FRONT + "## Something else\n\n> hello\n")
        self.assertEqual(d["system"], "")

    def test_a_deeper_heading_does_not_end_the_section(self):
        d = bootstrap.parse_def(ENGLISH.replace("Channel scope", "### Note\n> More."))
        self.assertIn("More.", d["system"])


class EmptyPromptDoesNotRun(unittest.TestCase):
    def test_an_agent_without_a_prompt_is_not_spawned(self):
        d = bootstrap.parse_def(FRONT + "## Chat facet\n\nno blockquote here\n")
        with mock.patch.object(bootstrap, "fetch_def", return_value=d), \
             mock.patch.dict(os.environ, {"NSEC_BOUWER": "nsec1x"}), \
             redirect_stdout(io.StringIO()) as log:
            got = bootstrap.build_agents({"run": ["bouwer"]}, "base", {"bouwer": "npub1x"})
        self.assertEqual(got, {})
        self.assertIn("no system prompt", log.getvalue())

    def test_an_agent_with_a_prompt_is_spawned(self):
        d = bootstrap.parse_def(ENGLISH)
        with mock.patch.object(bootstrap, "fetch_def", return_value=d), \
             mock.patch.dict(os.environ, {"NSEC_BOUWER": "nsec1x"}), \
             redirect_stdout(io.StringIO()):
            got = bootstrap.build_agents({"run": ["bouwer"]}, "base", {"bouwer": "npub1x"})
        self.assertIn("bouwer", got)


if __name__ == "__main__":
    unittest.main()
