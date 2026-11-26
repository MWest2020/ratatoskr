# SPDX-License-Identifier: MIT
"""Per fixture: the input is proven dirty, the output clean and
byte-identical in its kept image data. Plus the built cases of design.md
"Tests"."""
import os
import struct
import unittest
import zlib

import image_prep
import image_strip
import image_testwalk

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(HERE, "testdata")
DIRT = (b"fixture-", b"Exif", b"<x:xmpmeta", b"ICC_PROFILE", b"Photoshop", b"TRAILER")
STRIP = {"png": image_strip.strip_png, "jpg": image_strip.strip_jpeg, "webp": image_strip.strip_webp}
SOUND = {"png": image_testwalk.png_sound, "jpg": image_testwalk.jpeg_sound, "webp": image_testwalk.webp_sound}
PARTS = {"png": image_testwalk.png_parts, "jpg": image_testwalk.jpeg_segments, "webp": image_testwalk.webp_chunks}
ALLOW = {"png": {"IHDR", "PLTE", "tRNS", "IDAT", "IEND"},
         "jpg": {0xD8, 0xE0, 0xDB, 0xC4, 0xDD, 0xC0, 0xC1, 0xC2, 0xDA, 0xD9},
         "webp": {"VP8X", "ALPH", "VP8 ", "VP8L"}}
CLAIMED = {
    "dirty.png": {"gAMA", "iCCP", "pHYs", "tEXt", "zTXt", "iTXt", "eXIf", "tIME", "prVt"},
    "dirty.jpg": {0xE0, 0xE1, 0xE2, 0xED, 0xFE}, "dirty-progressive.jpg": {0xE0, 0xE1, 0xE2, 0xED, 0xFE},
    "dirty-restart.jpg": {0xE0, 0xE1, 0xE2, 0xED, 0xFE, 0xDD},
    "dirty-lossy.webp": {"ICCP", "EXIF", "XMP ", "fxTR"}, "dirty-lossless.webp": {"ICCP", "EXIF", "XMP ", "fxTR"},
    "dirty-lossy-alpha.webp": {"ICCP", "EXIF", "XMP ", "fxTR", "ALPH"}}
DIRTY = (("dirty.png", "png"), ("dirty.jpg", "jpg"), ("dirty-progressive.jpg", "jpg"),
         ("dirty-restart.jpg", "jpg"), ("dirty-lossy.webp", "webp"), ("dirty-lossless.webp", "webp"),
         ("dirty-lossy-alpha.webp", "webp"))
CLEAN_EXC = (image_strip.Refused, ValueError, IndexError, struct.error)
VP8 = b"\x00\x00\x00\x9d\x01\x2a\x02\x00\x02\x00"   # a 2x2 VP8 key frame
FORM = {"dirty.png": ["IHDR", "IDAT", "IDAT", "IEND"], "dirty-lossy.webp": ["VP8 "], "dirty-lossless.webp": ["VP8L"],
        "dirty-lossy-alpha.webp": ["VP8X", "ALPH", "VP8 "]}   # design.md fixture table, "Expected"

def _read(name):
    with open(os.path.join(TESTDATA, name), "rb") as f:
        return f.read()
def _image_bytes(fmt, parts):
    if fmt == "png": return b"".join(b for t, b in parts if t in ("IHDR", "PLTE", "tRNS", "IDAT"))
    if fmt == "jpg": return b"".join(p for m, p in parts if m in (0xDB, 0xC4, 0xDD, 0xC0, 0xC1, 0xC2, 0xDA))
    return b"".join(b for t, b in parts if t in ("VP8 ", "VP8L", "ALPH"))

def _png_chunk(ctype, body):
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)

def _png(extra=(), ihdr=None, idat=b"x"):
    ihdr = ihdr if ihdr is not None else struct.pack(">IIBBBBB", 2, 2, 8, 0, 0, 0, 0)
    chunks = [_png_chunk(b"IHDR", ihdr)] + [_png_chunk(t, b) for t, b in extra]
    chunks += [_png_chunk(b"IDAT", idat), _png_chunk(b"IEND", b"")]
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)

def _jseg(marker, payload):
    return bytes((0xFF, marker)) + struct.pack(">H", len(payload) + 2) + payload

def _jpeg(segments, prefix=b"\xff\xd8"):
    return prefix + b"".join(_jseg(m, p) for m, p in segments) + b"\xff\xd9"
SOF3 = struct.pack(">BHHB", 8, 2, 2, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00"
def _wchunk(ctype, body):
    return ctype + struct.pack("<I", len(body)) + body + (b"\x00" if len(body) % 2 else b"")

def _webp(chunks, size=None):
    body = b"WEBP" + b"".join(_wchunk(t, b) for t, b in chunks)
    return b"RIFF" + struct.pack("<I", size if size is not None else len(body)) + body
class DirtyFixturesAreStrippedClean(unittest.TestCase):
    def test_each_dirty_fixture(self):
        for name, fmt in DIRTY:
            with self.subTest(name):
                data = _read(name)
                self.assertIn(b"fixture-", data)
                present = {p[0] for p in PARTS[fmt](data)}
                self.assertTrue(CLAIMED[name] <= present, CLAIMED[name] - present)
                out, w, h = STRIP[fmt](data)
                for d in DIRT:
                    self.assertNotIn(d, out)
                self.assertTrue(SOUND[fmt](out))
                self.assertEqual((w, h), (24, 16))
                kept = {p[0] for p in PARTS[fmt](out)}
                self.assertTrue(kept <= ALLOW[fmt], kept - ALLOW[fmt])
                self.assertEqual(_image_bytes(fmt, PARTS[fmt](data)), _image_bytes(fmt, PARTS[fmt](out)))
                if name in FORM:
                    self.assertEqual([p[0] for p in PARTS[fmt](out)], FORM[name])
                if name == "dirty-lossy-alpha.webp": self.assertEqual(PARTS[fmt](out)[0][1][0], 0x10)

class RefusedFixtures(unittest.TestCase):
    CASES = (("rotated.png", "png", "orientation 6"), ("rotated.jpg", "jpg", "orientation 6"),
             ("cmyk.jpg", "jpg", "APP14"), ("animated.webp", "webp", "animated"))

    def test_each(self):
        for name, fmt, want in self.CASES:
            with self.subTest(name):
                with self.assertRaises(image_strip.Refused) as c:
                    STRIP[fmt](_read(name))
                self.assertIn(want, str(c.exception))

class PngBuiltCases(unittest.TestCase):
    def test_palette_png_keeps_plte_and_trns(self):
        extra = [(b"PLTE", b"\x01\x02\x03\x04\x05\x06"), (b"tRNS", b"\x00\x01"), (b"tEXt", b"Author\x00x")]
        out, w, h = image_strip.strip_png(_png(extra=extra, ihdr=struct.pack(">IIBBBBB", 2, 2, 8, 3, 0, 0, 0)))
        self.assertIn(_png_chunk(b"PLTE", b"\x01\x02\x03\x04\x05\x06"), out)
        self.assertIn(_png_chunk(b"tRNS", b"\x00\x01"), out)
        self.assertNotIn(b"tEXt", out)

    def test_huge_ihdr_dimensions_are_not_rejected_by_the_walker(self):
        _, w, h = image_strip.strip_png(_png(ihdr=struct.pack(">IIBBBBB", 20000, 20000, 8, 0, 0, 0, 0)))
        self.assertEqual((w, h), (20000, 20000))

    def test_exif_without_orientation_is_accepted(self):
        tiff = b"MM\x00\x2a" + struct.pack(">I", 8) + struct.pack(">H", 0)
        image_strip.strip_png(_png(extra=[(b"eXIf", tiff)]))   # must not raise

    def test_an_idat_over_5mib_is_refused_by_prepare(self):
        with self.assertRaises(image_strip.Refused) as c:
            image_prep.prepare(_png(idat=b"\x00" * (5 * 1024 * 1024 + 600 * 1024)))
        self.assertIn("byte limit", str(c.exception))

    REFUSALS = (
        ("flipped CRC", lambda: (lambda d: d[:-1] + bytes([d[-1] ^ 0xFF]))(_png()), "bad CRC"),
        ("truncated", lambda: _read("dirty.png")[:40], None),
        ("unknown critical chunk", lambda: _png(extra=[(b"ZZZZ", b"x")]), "unknown critical chunk"),
        ("IHDR not first", lambda: b"\x89PNG\r\n\x1a\n" + _png_chunk(b"gAMA", b"\x00\x00\xb1\x8f") + _png()[8:], "first chunk"),
        ("second IHDR", lambda: b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 0, 0, 0, 0)) * 2 + _png_chunk(b"IDAT", b"x") + _png_chunk(b"IEND", b""), "duplicate"),
        ("IHDR of 12 bytes", lambda: _png(ihdr=b"x" * 12), "13 bytes"),
        ("PLTE of 10 bytes", lambda: _png(extra=[(b"PLTE", b"x" * 10)]), "PLTE"),
        ("acTL", lambda: _png(extra=[(b"acTL", b"\x00" * 8)]), "animated PNG"),
        ("eXIf garbage", lambda: _png(extra=[(b"eXIf", b"not a tiff block")]), None),
    )

    def test_refusals(self):
        for name, build, want in self.REFUSALS:
            with self.subTest(name):
                with self.assertRaises(CLEAN_EXC) as c:
                    image_strip.strip_png(build())
                if want:
                    self.assertIsInstance(c.exception, image_strip.Refused)
                    self.assertIn(want, str(c.exception))

class JpegBuiltCases(unittest.TestCase):
    def test_fill_bytes_before_a_marker_are_accepted_and_not_copied(self):
        data = b"\xff\xd8\xff\xff\xc0" + struct.pack(">H", len(SOF3) + 2) + SOF3 + b"\xff\xd9"
        out, w, h = image_strip.strip_jpeg(data)
        self.assertEqual((w, h), (2, 2))
        self.assertNotIn(b"\xff\xff\xc0", out)

    REFUSALS = (
        ("cut before EOI", lambda: _read("dirty.jpg")[:_read("dirty.jpg").rfind(b"\xff\xd9")], None),
        ("unknown marker", lambda: _jpeg([(0xC8, b"")]), "unsupported marker"),
        ("SOF3", lambda: _jpeg([(0xC3, SOF3)]), "0xC3"),
        ("SOF9", lambda: _jpeg([(0xC9, SOF3)]), "0xC9"),
        ("4 components, no APP14", lambda: _jpeg([(0xC0, struct.pack(">BHHB", 8, 2, 2, 4) + b"\x01\x11\x00" * 4)]), "not 1 or 3"),
        ("RGB component IDs", lambda: _jpeg([(0xC0, struct.pack(">BHHB", 8, 2, 2, 3) + b"\x52\x11\x00\x47\x11\x00\x42\x11\x00")]), "RGB-coded"),
        ("second SOF", lambda: _jpeg([(0xC0, SOF3), (0xC0, SOF3)]), "duplicate SOF"),
        ("height 0", lambda: _jpeg([(0xC0, struct.pack(">BHHB", 8, 0, 2, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00")]), "DNL"),
        ("segment length 1", lambda: b"\xff\xd8\xff\xdb\x00\x01\xff\xd9", "below 2"),
        ("non-FF marker byte", lambda: b"\xff\xd8" + _jseg(0xC0, SOF3) + b"\x00\x00", "expected a marker"),
        ("DQT one byte too long", lambda: _jpeg([(0xDB, bytes(65) + b"\x00")]), None),
    )

    def test_refusals(self):
        for name, build, want in self.REFUSALS:
            with self.subTest(name):
                with self.assertRaises(CLEAN_EXC) as c:
                    image_strip.strip_jpeg(build())
                if want:
                    self.assertIsInstance(c.exception, image_strip.Refused)
                    self.assertIn(want, str(c.exception))

class WebpBuiltCases(unittest.TestCase):
    REFUSALS = (
        ("RIFF size one too large", lambda: _webp([(b"VP8 ", VP8)], size=len(_webp([(b"VP8 ", VP8)])) + 1), "RIFF size"),
        ("chunk size past the end", lambda: b"RIFF" + struct.pack("<I", 16) + b"WEBPVP8 " + struct.pack("<I", 100) + b"abcd", "past the end"),
        ("ALPH next to VP8L", lambda: _webp([(b"ALPH", b"\x00" * 4), (b"VP8L", b"\x2f\x00\x00\x00\x00")]), "ALPH next to VP8L"),
        ("two VP8 chunks", lambda: _webp([(b"VP8 ", VP8), (b"VP8 ", VP8)]), "more than one image chunk"),
        ("VP8X animation flag, no ANIM", lambda: _webp([(b"VP8X", bytes((0x02, 0, 0, 0, 1, 0, 0, 1, 0, 0))), (b"VP8 ", VP8)]), "animated"),
        ("VP8X canvas mismatch", lambda: _webp([(b"VP8X", bytes((0x00, 0, 0, 0, 9, 0, 0, 9, 0, 0))), (b"VP8 ", VP8)]), "canvas"),
    )

    def test_refusals(self):
        for name, build, want in self.REFUSALS:
            with self.subTest(name):
                with self.assertRaises(image_strip.Refused) as c:
                    image_strip.strip_webp(build())
                self.assertIn(want, str(c.exception))

class OtherFiles(unittest.TestCase):
    CASES = (("too large", b"\x00" * (20 * 1024 * 1024 + 1), "exceeds"),
             ("SVG text", b"<svg xmlns='x'></svg>", "SVG"),
             ("GIF bytes", b"GIF89a" + b"\x00" * 10, "GIF"),
             ("empty file", b"", "unknown file type"))

    def test_refusals(self):
        for name, data, want in self.CASES:
            with self.subTest(name):
                with self.assertRaises(image_strip.Refused) as c:
                    image_prep.prepare(data)
                self.assertIn(want, str(c.exception))

if __name__ == "__main__":
    unittest.main()
