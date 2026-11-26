# SPDX-License-Identifier: MIT
"""Bounded parsing never hangs and never crashes uncleanly: every
truncation and every single-byte flip of every fixture is either accepted
cleanly or refused, nothing else. See design.md "Tests"."""
import os
import random
import signal
import subprocess
import sys
import tempfile
import unittest

import image_prep
import image_strip
import image_testwalk

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(HERE, "testdata")
IMAGE_PREP = os.path.join(HERE, "image_prep.py")
FIXTURES = ("dirty.png", "rotated.png", "dirty.jpg", "dirty-progressive.jpg", "dirty-restart.jpg",
            "rotated.jpg", "cmyk.jpg", "dirty-lossy.webp", "dirty-lossless.webp",
            "dirty-lossy-alpha.webp", "animated.webp")
SOUND = {"png": image_testwalk.png_sound, "jpg": image_testwalk.jpeg_sound, "webp": image_testwalk.webp_sound}


def _read(name):
    with open(os.path.join(TESTDATA, name), "rb") as f:
        return f.read()


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout("prepare() took over 120s")


signal.signal(signal.SIGALRM, _alarm)


def _check(data, where):
    """A clean accept or a Refused; anything else fails and names where."""
    signal.alarm(120)
    try:
        out, fmt = image_prep.prepare(data)
    except image_strip.Refused:
        return
    except Exception as e:
        raise AssertionError(f"{where}: unclean failure {type(e).__name__}: {e}") from e
    finally:
        signal.alarm(0)
    if not SOUND[fmt](out):
        raise AssertionError(f"{where}: accepted output is not well-formed")


class TruncationSweep(unittest.TestCase):
    def test_every_length_of_every_fixture(self):
        for name in FIXTURES:
            data = _read(name)
            for n in range(0, len(data) + 1):
                _check(data[:n], f"{name}[:{n}]")


class ByteFlipSweep(unittest.TestCase):
    def test_200_flips_of_every_fixture(self):
        rng = random.Random(243)
        for name in FIXTURES:
            data = _read(name)
            for i in range(200):
                pos, val = rng.randrange(len(data)), rng.randrange(256)
                mutated = bytearray(data)
                mutated[pos] = val
                _check(bytes(mutated), f"{name} flip#{i} pos={pos} val={val}")


class CliOnATruncatedFile(unittest.TestCase):
    def test_exit_2_no_traceback(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(_read("dirty.png")[:40])
            path = f.name
        try:
            with tempfile.TemporaryDirectory() as outdir:
                r = subprocess.run([sys.executable, IMAGE_PREP, path, outdir], capture_output=True, text=True)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith("image_prep:"))
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
