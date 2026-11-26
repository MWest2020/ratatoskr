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

import image_testwalk
import test_image_strip as built   # the built cases; module import only, so its classes do not run twice

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


def _with_tempfile(data, run, name="shot.png"):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, name)
        with open(path, "wb") as f:
            f.write(data)
        return run(path)


def _sparse_run(size):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "big.png")
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        os.truncate(path, size)
        return _run(path)


def _dup_vp8x():
    vp8x = bytes((0x00, 0, 0, 0, 1, 0, 0, 1, 0, 0))
    return built._webp([(b"VP8X", vp8x), (b"VP8X", vp8x), (b"VP8 ", built.VP8)])


def _sos_too_long():
    sos = b"\x01\x01\x00\x00\x3f\x00\x00"   # Ns=1 needs 6 bytes, this is 7
    return b"\xff\xd8" + built._jseg(0xC0, built.SOF3) + built._jseg(0xDA, sos) + b"\x00\xff\xd9"


def _built_refusals():
    """(name, file name, bytes, reason or None) for every built refusal."""
    for cls in (built.PngBuiltCases, built.JpegBuiltCases, built.WebpBuiltCases):
        for name, build, want in cls.REFUSALS:
            yield name, "shot.png", build(), want
    yield "IHDR claiming 20000x20000", "shot.png", built._png(ihdr=struct.pack(">IIBBBBB", 20000, 20000, 8, 0, 0, 0, 0)), \
        "20000x20000 exceeds 2560 px"
    yield "IDAT over 5 MiB", "shot.png", built._png(idat=b"\x00" * (5 * 1024 * 1024 + 600 * 1024)), "byte limit"
    yield "SVG text in shot.png", "shot.png", b"  <svg xmlns='x'></svg>", "SVG"
    yield "GIF89a in x.png", "x.png", b"GIF89a" + b"\x00" * 10, "GIF"
    yield "empty file", "shot.png", b"", "unknown file type"
    yield "duplicate VP8X", "shot.webp", _dup_vp8x(), "duplicate VP8X"
    yield "SOS header one byte too long", "shot.jpg", _sos_too_long(), "SOS header length"


class TheCli(unittest.TestCase):
    def test_dirty_jpg_is_accepted_and_clean(self):
        r, files, out = _run(os.path.join(TESTDATA, "dirty.jpg"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(files, ["image.jpg"])
        self.assertEqual(r.stdout.strip(), os.path.join(os.path.dirname(r.stdout.strip()), "image.jpg"))
        for dirt in built.DIRT:   # (b): no metadata left, only keep-list segments, sound structure
            self.assertNotIn(dirt, out)
        self.assertTrue({m for m, _ in image_testwalk.jpeg_segments(out)} <= built.ALLOW["jpg"])
        self.assertTrue(image_testwalk.jpeg_sound(out))

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

    def test_every_built_refusal_exits_2_with_its_reason_and_writes_nothing(self):
        for name, fname, data, want in _built_refusals():
            with self.subTest(name):
                r, files, out = _with_tempfile(data, _run, fname)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertTrue(r.stderr.startswith("image_prep: "), r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                if want:
                    self.assertIn(want, r.stderr)
                self.assertEqual(files, [])

    def test_a_sparse_21_mib_file_is_refused_by_the_read_cap(self):
        r, files, out = _sparse_run(21 * 1024 * 1024)
        self.assertEqual(r.returncode, 2)
        self.assertIn("image_prep: input exceeds", r.stderr)
        self.assertEqual(files, [])

    def test_a_directory_is_not_a_regular_file(self):
        with tempfile.TemporaryDirectory() as d:
            r, files, out = _run(d)
        self.assertEqual((r.returncode, r.stderr.strip()), (2, "image_prep: not a regular file"))

    def test_a_malformed_file_exits_2_cleanly_and_writes_nothing(self):
        r, files, out = _with_tempfile(b"not a png at all", _run)
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith("image_prep: "))
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
