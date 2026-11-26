# SPDX-License-Identifier: MIT
"""The CLI: python3 image_prep.py <src> <outdir>. Exit codes, the stderr
text and the 2560 px refusal message. See design.md "Tests"."""
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(HERE, "testdata")
IMAGE_PREP = os.path.join(HERE, "image_prep.py")


def _run(src):
    with tempfile.TemporaryDirectory() as outdir:
        r = subprocess.run([sys.executable, IMAGE_PREP, src, outdir], capture_output=True, text=True)
        files = os.listdir(outdir)
        out = None
        if files:
            with open(os.path.join(outdir, files[0]), "rb") as f:
                out = f.read()
        return r, files, out


def _chunk(ctype, body):
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)


def _huge_png():
    ihdr = struct.pack(">IIBBBBB", 2880, 1800, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", b"x") + _chunk(b"IEND", b"")


def _with_tempfile(data, run):
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        tmp.write(data)
        tmp.close()
        return run(tmp.name)
    finally:
        os.unlink(tmp.name)


class TheCli(unittest.TestCase):
    def test_dirty_jpg_is_accepted_and_clean(self):
        r, files, out = _run(os.path.join(TESTDATA, "dirty.jpg"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(files, ["image.jpg"])
        self.assertTrue(r.stdout.strip().endswith("image.jpg"))
        self.assertNotIn(b"Exif", out)

    def test_rotated_images_exit_2_with_orientation(self):
        for name in ("rotated.jpg", "rotated.png"):
            with self.subTest(name):
                r, files, out = _run(os.path.join(TESTDATA, name))
                self.assertEqual(r.returncode, 2)
                self.assertIn("image_prep: orientation 6", r.stderr)
                self.assertEqual(files, [])

    def test_oversized_image_names_the_traps_and_the_fixes(self):
        r, files, out = _with_tempfile(_huge_png(), _run)
        self.assertEqual(r.returncode, 2)
        for want in ("2560", "fullPage", 'scale: "css"', "figsize"):
            self.assertIn(want, r.stderr)
        self.assertEqual(files, [])

    def test_a_malformed_file_exits_2_cleanly_and_writes_nothing(self):
        r, files, out = _with_tempfile(b"not a png at all", _run)
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith("image_prep: "))
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
