# SPDX-License-Identifier: EUPL-1.2
"""Input validation of the GitHub read layer.

Why this exists: `/api/prs?repo=boomhuis` (without an owner) went unchecked
through to the GitHub API and came back as a **502 with raw upstream text**. An
input error posing as an outage, and the user sees "HTTP Error 404: Not Found"
instead of "expected owner/name".
"""
import unittest

import github


class ValidRepoTest(unittest.TestCase):
    def test_owner_slash_name_is_valid(self):
        for name in ("MWest2020/boomhuis", "a/b", "MWest2020/internetnl-cli",
                     "MWest2020/Road_to_el_DORA-do", "org.io/repo.js"):
            self.assertTrue(github.valid_repo(name), name)

    def test_without_an_owner_is_invalid(self):
        self.assertFalse(github.valid_repo("boomhuis"))

    def test_path_characters_do_not_get_through(self):
        # Every segment must start with an alphanumeric character, otherwise ".."
        # and "." slip through and a path-like value ends up in the URL.
        for name in ("../x", "./x", "a/..", "a/../b", "a/b/c", "/x", "x/"):
            self.assertFalse(github.valid_repo(name), name)

    def test_empty_and_whitespace_are_invalid(self):
        for name in ("", None, "a b/c", "a/b c", " a/b"):
            self.assertFalse(github.valid_repo(name), repr(name))

    def test_length_is_bounded(self):
        self.assertFalse(github.valid_repo("a" * 200 + "/b"))


if __name__ == "__main__":
    unittest.main()
