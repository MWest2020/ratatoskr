# SPDX-License-Identifier: MIT
"""ping.sh --image, pinned at the argv level with fake buzz/sops/uv on PATH.

This fake does NOT prove the real CLI accepts `--content '<caption>' --file
<path>` — that is the live check (gate 3, tasks.md 3.1). It proves which argv
`ping.sh` builds: the caption as the `--content` VALUE, `--file` alongside it,
and no stdin `-` anywhere once `--file` is in play. Every IDENT/channel rule
is the existing, untouched code path — only the branch before the send is new.
"""
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PING = os.path.join(HERE, "ping.sh")

FAKE_SOPS = "#!/bin/sh\nprintf 'identities:\\n  bouwer:\\n    nsec: nsec1faketestsecret\\n'\n"
FAKE_BUZZ = '#!/bin/sh\nfor a in "$@"; do printf \'%s\\t\' "$a"; done >> "$CALLS_FILE"\nprintf \'\\n\' >> "$CALLS_FILE"\n'
FAKE_UV = """#!/bin/sh
shift                    # drop "run"
shift                    # drop the image_prep.py path (the fake ignores it)
src="$1"; outdir="$2"
echo "$outdir" > "$OUTDIR_RECORD"
case "$src" in
  *refuse*) echo "image_prep: refused (fake)" >&2; exit 2 ;;
esac
out="$outdir/prepared.png"
printf 'PNGDATA' > "$out"
echo "$out"
"""


def _write(path, body):
    with open(path, "w") as f:
        f.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class PingImage(unittest.TestCase):
    def setUp(self):
        self.fakebin = tempfile.mkdtemp()
        self.work = tempfile.mkdtemp()
        self.calls = os.path.join(self.work, "buzz.calls")
        self.outdir_record = os.path.join(self.work, "outdir.txt")
        open(self.calls, "w").close()
        _write(os.path.join(self.fakebin, "sops"), FAKE_SOPS)
        _write(os.path.join(self.fakebin, "uv"), FAKE_UV)
        # ping.sh calls ~/.local/bin/buzz by a fixed path, not a PATH lookup
        # (the same as the real install on agent-lxc); the fake HOME gives it
        # the fake binary without touching that line.
        self.fakehome = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.fakehome, ".local", "bin"))
        _write(os.path.join(self.fakehome, ".local", "bin", "buzz"), FAKE_BUZZ)
        self.img = os.path.join(self.work, "chart.png")
        open(self.img, "w").write("not a real image, the fake uv does not care")
        self.refused_img = os.path.join(self.work, "refuse-me.png")
        open(self.refused_img, "w").write("x")

    def _env(self, ident):
        return dict(os.environ, IDENT=ident, PATH=self.fakebin + ":" + os.environ["PATH"],
                   HOME=self.fakehome, SOPS_AGE_KEY_FILE="/dev/null",
                   CALLS_FILE=self.calls, OUTDIR_RECORD=self.outdir_record)

    def _run(self, args, ident="bouwer", chan="statistics", stdin=""):
        return subprocess.run(["bash", PING, *args], env=dict(self._env(ident), CHAN=chan),
                              input=stdin, capture_output=True, text=True, timeout=30)

    def _calls(self):
        with open(self.calls) as f:
            return [ln.rstrip("\t").split("\t") for ln in f.read().splitlines()]

    def test_image_branch_sends_caption_as_content_value_with_file_no_dash(self):
        r = self._run(["--image", self.img, "p95 latency, last 7 days"])
        self.assertEqual(r.returncode, 0, r.stderr)
        (argv,) = self._calls()
        self.assertIn("--file", argv)
        i = argv.index("--content")
        self.assertEqual(argv[i + 1], "p95 latency, last 7 days")
        self.assertNotIn("-", argv[i:])  # no stdin anywhere once --file is used

    def test_text_only_branch_still_uses_stdin_dash(self):
        r = self._run([], stdin="hello")
        self.assertEqual(r.returncode, 0, r.stderr)
        (argv,) = self._calls()
        i = argv.index("--content")
        self.assertEqual(argv[i + 1], "-")
        self.assertNotIn("--file", argv)

    def test_the_temp_directory_is_gone_after_the_send(self):
        r = self._run(["--image", self.img, "caption"])
        self.assertEqual(r.returncode, 0, r.stderr)
        outdir = open(self.outdir_record).read().strip()
        self.assertTrue(outdir)
        self.assertFalse(os.path.exists(outdir))

    def test_a_refused_image_exits_10_and_never_sends(self):
        r = self._run(["--image", self.refused_img, "caption"])
        self.assertEqual(r.returncode, 10)
        self.assertIn("geweigerd", r.stderr)
        self.assertEqual(self._calls(), [])

    def test_a_missing_caption_exits_9_and_never_sends(self):
        r = self._run(["--image", self.img])
        self.assertEqual(r.returncode, 9)
        self.assertEqual(self._calls(), [])

    def test_a_human_ident_is_still_refused_with_image(self):
        r = self._run(["--image", self.img, "caption"], ident="mark")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("mens-identiteit", r.stderr)
        self.assertEqual(self._calls(), [])


if __name__ == "__main__":
    unittest.main()
