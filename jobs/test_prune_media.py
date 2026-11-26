# SPDX-License-Identifier: MIT
"""jobs/prune-media.sh against a fake ssh: the prune runs first, then the size
check, and a store over MEDIA_MAX_BYTES fails loudly (rc 1, size and limit in
English on stderr) so the timer check reports it. No network, no relay."""
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "prune-media.sh")
FAKE_SSH = r"""#!/usr/bin/env bash
# args: -o BatchMode=yes <host> <command>
printf '%s\t%s\n' "$3" "$4" >> "$SSH_LOG"
case "$4" in
  *" size "*) [ "${SIZE_RC:-0}" = 0 ] || exit "$SIZE_RC"
              echo "Creating buzz_media-prune_run ... done" >&2
              printf '%s\n' "${SIZE_OUT:-{\"count\":3,\"bytes\":$FAKE_BYTES,\"sizeless\":0}}" ;;
  *) echo "INFO  : x.png: Deleted"; exit "${PRUNE_RC:-0}" ;;
esac
"""
RUN = "cd /opt/buzz-relay && sudo docker compose --profile maintenance run --rm media-prune"


class PruneMedia(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        ssh = os.path.join(self.tmp.name, "ssh")
        with open(ssh, "w") as f:
            f.write(FAKE_SSH)
        os.chmod(ssh, os.stat(ssh).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.tmp.name, "ssh.log")
        self.env = dict(os.environ, PATH=self.tmp.name + os.pathsep + os.environ["PATH"],
                        SSH_LOG=self.log, MEDIA_MAX_BYTES="1000")
        for k in ("MEDIA_SSH", "MEDIA_DIR", "MEDIA_BUCKET"):
            self.env.pop(k, None)

    def run_script(self, **env):
        return subprocess.run(["bash", SCRIPT], env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=30)

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return [ln.rstrip("\n").split("\t") for ln in f]

    def test_the_script_parses(self):
        self.assertEqual(subprocess.run(["bash", "-n", SCRIPT]).returncode, 0)

    def test_prune_then_a_size_under_the_limit_is_rc_0(self):
        r = self.run_script(FAKE_BYTES="999")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls(), [["buzz-relay", RUN],
                                        ["buzz-relay", RUN + " size dst:buzz-media --json"]])
        self.assertIn("media store is 999 bytes, under the limit of 1000", r.stdout)

    def test_a_size_over_the_limit_is_rc_1_with_the_reason(self):
        r = self.run_script(FAKE_BYTES="5000")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(self.calls()), 2)   # the prune did run first
        self.assertIn("media store is 5000 bytes after the prune, over the MEDIA_MAX_BYTES "
                      "limit of 1000: busier than expected, not deliberate growth", r.stderr)

    def test_the_default_limit_is_2_gib(self):
        env = dict(self.env)
        env.pop("MEDIA_MAX_BYTES")
        r = subprocess.run(["bash", SCRIPT], env=dict(env, FAKE_BYTES=str(2 * 1024 ** 3 + 1)),
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 1)
        self.assertIn("limit of 2147483648", r.stderr)

    def test_a_failed_prune_stops_before_the_size_check(self):
        r = self.run_script(FAKE_BYTES="1", PRUNE_RC="3")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[media-prune] prune failed on buzz-relay (rc=3)", r.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_a_failed_size_check_is_named(self):
        r = self.run_script(FAKE_BYTES="1", SIZE_RC="255")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[media-prune] size check failed on buzz-relay (rc=255)", r.stderr)

    def test_output_without_a_byte_count_is_not_read_as_zero(self):
        r = self.run_script(SIZE_OUT="permission denied")
        self.assertEqual(r.returncode, 1)
        self.assertIn("size check gave no byte count: permission denied", r.stderr)

    def test_host_and_bucket_are_configurable(self):
        r = self.run_script(FAKE_BYTES="1", MEDIA_SSH="relay2", MEDIA_BUCKET="other")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls()[1], ["relay2", RUN + " size dst:other --json"])


if __name__ == "__main__":
    unittest.main()
