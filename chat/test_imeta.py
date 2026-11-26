# SPDX-License-Identifier: MIT
"""imeta: the one reader of a message's image tags, pinned against the one
recorded event (chat/testdata/imeta-event.json, gate 1.1 of
agent-image-to-chat). A malformed tag never raises: no images, content as is."""
import json
import os
import unittest

import imeta

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "testdata", "imeta-event.json")) as f:
    EVENT = json.load(f)
SHA = "bc9854f99dbe38c18f0ae3d55ad8fc7583c03b645fdc7be1ee68524a2888871e"
URL = f"http://192.168.178.60:3000/media/{SHA}.png"
CAPTION = "gate 1.1 imeta probe (#243) — 16x16 test image, deleted right after"
MALFORMED = {
    "imeta without fields": [["imeta"]],
    "a non-string field": [["imeta", 7]],
    "a None field": [["imeta", None]],
    "a field without a space": [["imeta", "m"]],
    "an entry that is not a list": ["imeta"],
    "tags as a string": "imeta url x",
    "tags as a dict": {"imeta": ["m image/png"]},
    "tags missing": None,
}


class TheRecordedEvent(unittest.TestCase):
    def test_from_tags_gives_the_one_image(self):
        self.assertEqual(imeta.from_tags(EVENT["tags"]), [
            {"url": URL, "m": "image/png", "x": SHA, "size": "463", "dim": "16x16"}])

    def test_clean_content_removes_the_whole_markdown_line(self):
        clean = imeta.clean_content(EVENT["content"], EVENT["tags"])
        self.assertEqual(clean, CAPTION)
        self.assertNotIn("![image]", clean)
        self.assertNotIn("/media/", clean)

    def test_an_image_without_a_caption_cleans_to_empty(self):
        self.assertEqual(imeta.clean_content(f"![image]({URL})", EVENT["tags"]), "")

    def test_the_h_tag_alone_is_no_image(self):
        tags = [t for t in EVENT["tags"] if t[0] == "h"]
        self.assertEqual(imeta.from_tags(tags), [])
        self.assertEqual(imeta.clean_content(EVENT["content"], tags), EVENT["content"])

    def test_a_non_image_imeta_is_skipped(self):
        tags = [["imeta", f"url {URL}", "m application/pdf"]]
        self.assertEqual(imeta.from_tags(tags), [])

    def test_missing_keys_are_none(self):
        self.assertEqual(imeta.from_tags([["imeta", "m image/webp"]]),
                         [{"url": None, "m": "image/webp", "x": None, "size": None, "dim": None}])


class MalformedTagsNeverRaise(unittest.TestCase):
    def test_each_shape_gives_no_images_and_the_content_unchanged(self):
        for name, tags in MALFORMED.items():
            with self.subTest(name):
                self.assertEqual(imeta.from_tags(tags), [])
                self.assertEqual(imeta.clean_content(EVENT["content"], tags), EVENT["content"])

    def test_content_that_is_not_a_string_is_returned_as_is(self):
        self.assertIsNone(imeta.clean_content(None, EVENT["tags"]))


if __name__ == "__main__":
    unittest.main()
