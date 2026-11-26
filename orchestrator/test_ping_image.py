# SPDX-License-Identifier: MIT
"""ping.sh --image: the real IDENT/channel checks and the real
image_prep.py, against a fake buzz and a fake sops so no network or secret
is touched. Does not prove the real CLI — gate 3.1 does. See design.md
"The helper is ping.sh, extended"."""
import os
import stat
import subprocess
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PING = os.path.join(HERE, "ping.sh")
DIRTY_PNG = os.path.join(HERE, "testdata", "dirty.png")
ROTATED_PNG = os.path.join(HERE, "testdata", "rotated.png")

BUZZ_SH = '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$ARGV_LOG"\necho \'{"accepted":true}\'\n'   # one arg per line
SOPS_SH = ('#!/usr/bin/env bash\necho called >> "$SOPS_LOG"\n'
           'printf \'identities:\\n  bouwer: {nsec: nsec1fake}\\n  mark: {nsec: nsec1fake}\\n\'\n')


def _write_exe(path, text):
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


class PingImage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", self.tmp]))
        home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(home, ".local", "bin"))
        _write_exe(os.path.join(home, ".local", "bin", "buzz"), BUZZ_SH)
        binp = os.path.join(self.tmp, "bin")
        os.makedirs(binp)
        _write_exe(os.path.join(binp, "sops"), SOPS_SH)
        self.argv_log = os.path.join(self.tmp, "argv.log")
        self.sops_log = os.path.join(self.tmp, "sops.log")
        self.env = dict(os.environ, HOME=home, PATH=binp + os.pathsep + os.environ["PATH"],
                         ARGV_LOG=self.argv_log, SOPS_LOG=self.sops_log)

    def _run(self, *args, ident="bouwer", chan="general"):
        env = dict(self.env, IDENT=ident, CHAN=chan)
        return subprocess.run([PING, *args], cwd=ROOT, env=env, capture_output=True, text=True)

    def _logged(self, path):
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            return f.read()

    def test_argv_file_mention_and_temp_cleanup(self):
        caption = "p95 latency, last 7 days"
        r = self._run("--image", DIRTY_PNG, caption)
        self.assertEqual(r.returncode, 0, r.stderr)
        argv = self._logged(self.argv_log).splitlines()
        with open(os.path.join(ROOT, "identities.yml")) as f:
            npub = yaml.safe_load(f)["identities"]["bouwer"]["npub"]
        with open(os.path.join(ROOT, "channels.yml")) as f:
            cid = yaml.safe_load(f)["channels"]["general"]["id"]
        out_path = argv[7] if len(argv) > 7 else ""
        self.assertEqual(argv, ["messages", "send", "--channel", cid, "--content", caption,
                                "--file", out_path, "--mention", npub])
        self.assertEqual(os.path.basename(out_path), "image.png")
        self.assertFalse(os.path.exists(os.path.dirname(out_path)), "temp dir survived the send")

    def test_an_empty_image_path_is_refused_not_sent_as_text(self):
        r = self._run("--image", "", "caption")
        self.assertEqual(r.returncode, 10)
        self.assertIn("image_prep: not a regular file", r.stderr)
        self.assertEqual(self._logged(self.argv_log), "")

    def test_a_refused_image_sends_nothing_and_never_calls_sops(self):
        r = self._run("--image", ROTATED_PNG, "caption")
        self.assertEqual(r.returncode, 10)
        self.assertIn("image refused", r.stderr)
        self.assertEqual(self._logged(self.argv_log), "")
        self.assertEqual(self._logged(self.sops_log), "")

    def test_a_missing_caption_exits_9_before_sops(self):
        r = self._run("--image", DIRTY_PNG)
        self.assertEqual(r.returncode, 9)
        self.assertIn("caption", r.stderr)
        self.assertEqual(self._logged(self.sops_log), "")

    def test_a_human_ident_is_refused_before_the_helper_runs(self):
        # rotated.png would make the helper exit 10; exit 4 shows the IDENT check came first.
        r = self._run("--image", ROTATED_PNG, "caption", ident="mark")
        self.assertEqual(r.returncode, 4)
        self.assertNotIn("image_prep", r.stderr)
        self.assertEqual(self._logged(self.sops_log), "")
        self.assertEqual(self._logged(self.argv_log), "")

    def test_exit_9_and_10_stderr_are_english(self):
        r9 = self._run("--image", DIRTY_PNG)
        r10 = self._run("--image", ROTATED_PNG, "caption")
        self.assertEqual(r9.stderr, "[ping] an image needs a caption\n")
        self.assertEqual(r10.stderr, "image_prep: orientation 6: rotate the pixels before sending\n"
                                     "[ping] image refused (image_prep.py)\n")


if __name__ == "__main__":
    unittest.main()
