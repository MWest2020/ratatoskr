# SPDX-License-Identifier: MIT
"""jobs/prune-media.sh with a fake ssh on PATH: a prune, then a size check
that is loud above MEDIA_MAX_BYTES (design.md: a log line alone is the silent
failure AGENTS.md forbids)."""
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "prune-media.sh")

FAKE_SSH = """#!/bin/sh
# args: -o BatchMode=yes <host> <remote command...>
shift 2
echo "$2" >> "$CALLS_FILE"
case "$2" in
  *"size dst:"*) printf '{"bytes": %s}' "${FAKE_SIZE_BYTES:-0}" ;;
esac
exit 0
"""


def _write(path, body):
    with open(path, "w") as f:
        f.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class PruneMedia(unittest.TestCase):
    def setUp(self):
        self.fakebin = tempfile.mkdtemp()
        self.calls = os.path.join(self.fakebin, "calls.log")
        open(self.calls, "w").close()
        _write(os.path.join(self.fakebin, "ssh"), FAKE_SSH)

    def _run(self, size_bytes, max_bytes=None):
        env = dict(os.environ, PATH=self.fakebin + ":" + os.environ["PATH"],
                   CALLS_FILE=self.calls, FAKE_SIZE_BYTES=str(size_bytes))
        if max_bytes is not None:
            env["MEDIA_MAX_BYTES"] = str(max_bytes)
        return subprocess.run(["bash", SCRIPT], env=env, capture_output=True,
                              text=True, timeout=30)

    def _calls(self):
        with open(self.calls) as f:
            return f.read().splitlines()

    def test_a_prune_runs_before_the_size_check(self):
        self._run(1_000_000)
        calls = self._calls()
        self.assertEqual(len(calls), 2)
        self.assertNotIn("size dst:", calls[0])
        self.assertIn("size dst:", calls[1])

    def test_under_the_ceiling_is_rc_0(self):
        r = self._run(1_000_000, max_bytes=2 * 1024**3)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1000000 bytes", r.stdout)

    def test_over_the_ceiling_is_rc_1_with_the_reason_printed(self):
        r = self._run(3 * 1024**3, max_bytes=2 * 1024**3)
        self.assertEqual(r.returncode, 1)
        self.assertIn("over de grens", r.stderr)
        self.assertIn(str(3 * 1024**3), r.stderr)


if __name__ == "__main__":
    unittest.main()
