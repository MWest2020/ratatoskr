# SPDX-License-Identifier: MIT
"""The CLI's own guards, run in-process: the strip self-check against a stripper
that leaks, the capped read, and an unreadable source. See design.md
"Preparing the image", steps 1 and 7."""
import contextlib
import io
import os
import struct
import sys
import tempfile
import unittest
import zlib
from unittest import mock

import image_prep
import image_strip
from test_image_prep import TESTDATA, _run

DIRTY_PNG = os.path.join(TESTDATA, "dirty.png")


def _chunk(ctype, body):
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)


class _Endless:
    """A source that never ends: a read() without a size never returns."""
    def __init__(self, *_):
        self.sizes = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, n=-1):
        self.sizes.append(n)
        if n is None or n < 0:
            raise MemoryError("unbounded read() of an endless source")
        return b"\x89PNG\r\n\x1a\n" + bytes(n - 8)


def _main(src, **patch):
    """image_prep.main() in-process: (exit code, stderr, files written)."""
    with tempfile.TemporaryDirectory() as outdir, contextlib.ExitStack() as stack:
        for name, new in patch.items():
            stack.enter_context(mock.patch.object(image_prep if name == "open" else image_strip, name, new, create=True))
        stack.enter_context(mock.patch.object(sys, "argv", ["image_prep.py", src, outdir]))
        err = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        return image_prep.main(), err.getvalue(), os.listdir(outdir)


class GuardsOfTheCli(unittest.TestCase):
    def test_the_self_check_refuses_a_part_off_the_keep_list(self):
        real = image_strip.strip_png
        def leaky(data):   # the same leak on every call, so a re-strip alone would not see it
            out, w, h = real(data)
            return out[:-12] + _chunk(b"tEXt", b"Author\x00leak") + out[-12:], w, h
        rc, err, files = _main(DIRTY_PNG, strip_png=leaky)
        self.assertEqual((rc, files), (2, []))
        self.assertEqual(err, "image_prep: strip self-check failed: b'tEXt' is not on the keep-list\n")

    def test_the_read_is_capped_at_limit_plus_one(self):
        src = _Endless()
        rc, err, files = _main(DIRTY_PNG, open=lambda *a: src)
        self.assertEqual((rc, files, src.sizes), (2, [], [image_prep.LIMIT + 1]))
        self.assertIn("image_prep: input exceeds", err)

    def test_any_oserror_on_open_is_a_refusal(self):
        for exc in (PermissionError(13, "Permission denied"), OSError(5, "Input/output error")):
            with self.subTest(exc.strerror):
                rc, err, files = _main(DIRTY_PNG, open=mock.Mock(side_effect=exc))
                self.assertEqual((rc, err, files), (2, f"image_prep: cannot read the file: {exc.strerror}\n", []))

    def test_a_mode_000_source_exits_2_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "shot.png")
            with open(path, "wb") as f:
                f.write(b"not an image")
            os.chmod(path, 0)
            r, files, out = _run(path)
        self.assertEqual((r.returncode, files), (2, []))
        self.assertNotIn("Traceback", r.stderr)
        want = "image_prep: cannot read the file: Permission denied\n" if os.geteuid() else "image_prep: unknown file type\n"
        self.assertEqual(r.stderr, want)   # root reads a mode-000 file; the any-OSError case covers it there



if __name__ == "__main__":
    unittest.main()
