# SPDX-License-Identifier: MIT
"""orchestrator/image_prep.py runs through `uv run`, for real, with real Pillow.

This never skips: `test_a_pillow_resolves` is the guard, so a missing Pillow
is one red test, not a quiet green run of nothing (AGENTS.md: skipping does
not count as passing). Assertions are on the OUTPUT bytes, parsed here with
the standard library only — this file needs no Pillow, only the script does.
"""
import os
import struct
import subprocess
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "image_prep.py")
DATA = os.path.join(HERE, "testdata")


def run_prep(src, outdir):
    return subprocess.run(["uv", "run", SCRIPT, src, outdir],
                          capture_output=True, text=True, timeout=60)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def png_chunk_types(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG signature"
    pos, types = 8, []
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8].decode("ascii")
        types.append(ctype)
        pos += 8 + length + 4  # length + type + data + crc
    return types


def png_dims(data):
    return struct.unpack(">II", data[16:24])


def jpeg_marker_types(data):
    assert data[:2] == b"\xff\xd8", "not a JPEG SOI"
    pos, markers = 2, []
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            break
        marker = data[pos + 1]
        markers.append(marker)
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:  # SOI/EOI/RSTn: no length
            pos += 2
            continue
        (seg_len,) = struct.unpack(">H", data[pos + 2:pos + 4])
        if marker == 0xDA:  # SOS: scan data follows, stop scanning headers
            break
        pos += 2 + seg_len
    return markers


def jpeg_dims(data):
    """Width/height from the first SOFn marker (0xC0-0xCF, excluding DHT/DAC)."""
    pos = 2
    while pos < len(data) - 1:
        marker = data[pos + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[pos + 5:pos + 9])
            return w, h
        (seg_len,) = struct.unpack(">H", data[pos + 2:pos + 4])
        pos += 2 + seg_len
    raise AssertionError("no SOF marker found")


def webp_chunk_types(data):
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", "not a WebP RIFF"
    pos, types = 12, []
    while pos < len(data):
        ctype = data[pos:pos + 4].decode("ascii")
        (size,) = struct.unpack("<I", data[pos + 4:pos + 8])
        types.append(ctype)
        pos += 8 + size + (size % 2)  # chunks are padded to even size
    return types


def write_solid_png(path, w, h, rgb=(10, 120, 200)):
    """A valid RGB PNG, stdlib-only (no filtering, zlib level 6)."""
    row = bytes([0]) + bytes(rgb) * w
    raw = row * h
    idat = zlib.compress(raw)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)

    def chunk(ctype, data):
        t = ctype.encode("ascii")
        return (struct.pack(">I", len(data)) + t + data
                + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk("IHDR", ihdr))
        f.write(chunk("IDAT", idat))
        f.write(chunk("IEND", b""))


class APillowResolves(unittest.TestCase):
    """The guard: never skip. If this is red, every test below is suspect
    for the same reason, not for its own."""

    def test_a_pillow_resolves(self):
        r = subprocess.run(["uv", "run", "--with", "pillow>=11,<12", "python3", "-c",
                            "import PIL; print(PIL.__version__)"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         f"uv could not resolve Pillow — every test below is "
                         f"invalid until this is green: {r.stderr}")


class ARefusalGoesToStderrWithExit2(unittest.TestCase):
    def _refused(self, fixture, reason_snippet):
        with tempfile.TemporaryDirectory() as outdir:
            r = run_prep(os.path.join(DATA, fixture), outdir)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("refused", r.stderr)
        self.assertIn(reason_snippet, r.stderr)
        return r

    def test_an_svg_renamed_to_png_is_refused_by_magic_bytes(self):
        self._refused("svg-renamed.png", "not PNG, JPEG or WebP")

    def test_a_png_claiming_20000x20000_is_refused(self):
        self._refused("huge-dims.png", "too large")

    def test_a_truncated_png_is_refused(self):
        self._refused("truncated.png", "could not decode")

    def test_a_21_mib_file_is_refused_on_size_alone(self):
        r = self._refused("too-big.png", "20971520")
        self.assertIn("bytes", r.stderr)


class TheStripRemovesMetadataAndAppliesOrientation(unittest.TestCase):
    def test_png_keeps_only_image_chunks(self):
        with tempfile.TemporaryDirectory() as outdir:
            r = run_prep(os.path.join(DATA, "with-text-exif-icc.png"), outdir)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout.strip()
            self.assertTrue(os.path.exists(out))
            types = set(png_chunk_types(read_bytes(out)))
        self.assertLessEqual(types, {"IHDR", "PLTE", "tRNS", "IDAT", "IEND"})
        self.assertIn("IDAT", types)

    def test_jpeg_loses_app_segments_and_keeps_the_rotation(self):
        src = os.path.join(DATA, "with-exif-gps-orientation6.jpg")
        with tempfile.TemporaryDirectory() as outdir:
            r = run_prep(src, outdir)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout.strip()
            data = read_bytes(out)
        markers = jpeg_marker_types(data)
        # APP0 (0xE0, JFIF) is harmless and not metadata; APP1 (EXIF), APP2
        # (ICC) and COM (0xFE) must be gone.
        self.assertNotIn(0xE1, markers)
        self.assertNotIn(0xE2, markers)
        self.assertNotIn(0xFE, markers)
        # Orientation 6 on an 8x4 source swaps the dimensions once applied.
        self.assertEqual(jpeg_dims(data), (4, 8))

    def test_webp_loses_the_exif_chunk(self):
        with tempfile.TemporaryDirectory() as outdir:
            r = run_prep(os.path.join(DATA, "with-exif.webp"), outdir)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout.strip()
            types = set(webp_chunk_types(read_bytes(out)))
        self.assertNotIn("EXIF", types)
        self.assertNotIn("XMP ", types)
        self.assertNotIn("ICCP", types)


class TheOutputFitsTheCeilings(unittest.TestCase):
    def test_a_large_image_is_fit_inside_2560px_and_stays_under_5_mib(self):
        with tempfile.TemporaryDirectory() as workdir:
            src = os.path.join(workdir, "big.png")
            write_solid_png(src, 3000, 2000)
            outdir = os.path.join(workdir, "out")
            os.makedirs(outdir)
            r = run_prep(src, outdir)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout.strip()
            data = read_bytes(out)
        w, h = png_dims(data)
        self.assertLessEqual(max(w, h), 2560)
        self.assertLessEqual(len(data), 5 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
