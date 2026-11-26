# SPDX-License-Identifier: MIT
"""jobs/prune-media.sh against a fake ssh: the prune runs first, then the size
check, and a store over MEDIA_MAX_BYTES fails loudly (rc 1, size and limit in
English on stderr) so the timer check reports it. No network, no relay."""
import os
import stat
import subprocess
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "prune-media.sh")
COMPOSE = os.path.join(os.path.dirname(HERE), "deploy", "docker-compose.yml")
FAKE_SSH = r"""#!/usr/bin/env bash
# args: -o BatchMode=yes <host> <command>
printf '%s\t%s\n' "$3" "$4" >> "$SSH_LOG"
DEFAULT_OUT="{\"count\":3,\"bytes\":$FAKE_BYTES,\"sizeless\":0}"
case "$4" in
  *" size "*) [ "${SIZE_RC:-0}" = 0 ] || exit "$SIZE_RC"
              echo "Creating buzz_media-prune_run ... done" >&2
              printf '%s\n' "${SIZE_OUT:-$DEFAULT_OUT}" ;;
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
        for k in ("MEDIA_SSH", "MEDIA_DIR"):
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
                                        ["buzz-relay", RUN + " size media: --json"]])
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
        self.assertTrue(r.stderr.endswith("size check gave no byte count: permission denied\n"), r.stderr)

    def test_a_limit_that_is_not_a_number_is_refused_before_anything_runs(self):
        for bad in ("2G", "1e9", "-1", "12 34", "2147483648 "):
            with self.subTest(bad):
                if os.path.exists(self.log):
                    os.unlink(self.log)
                r = self.run_script(FAKE_BYTES="1", MEDIA_MAX_BYTES=bad)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(r.stderr, "[media-prune] MEDIA_MAX_BYTES must be a whole number of bytes, "
                                           f"got '{bad}'\n")
                self.assertEqual(self.calls(), [])

    def test_the_host_is_configurable_and_the_script_never_names_the_bucket(self):
        r = self.run_script(FAKE_BYTES="1", MEDIA_SSH="relay2", MEDIA_BUCKET="other")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls()[1], ["relay2", RUN + " size media: --json"])
        with open(SCRIPT) as f:
            self.assertNotIn("buzz-media", f.read())


class TheComposeService(unittest.TestCase):
    """The prune command is pinned: what it deletes is decided here, not on the host."""
    def test_the_media_prune_service(self):
        with open(COMPOSE) as f:
            services = yaml.safe_load(f)["services"]
        svc = services["media-prune"]
        self.assertEqual(svc["profiles"], ["maintenance"])
        self.assertEqual(svc["command"], ["delete", "media:", "--min-age", "30d",
                                          "--include", "*.{png,jpg,jpeg,webp}", "-v"])
        self.assertEqual(svc["environment"]["RCLONE_CONFIG_MEDIA_TYPE"], "alias")
        # one source for the bucket: the alias points at the relay's own bucket setting
        self.assertEqual(svc["environment"]["RCLONE_CONFIG_MEDIA_REMOTE"],
                         "dst:" + services["relay"]["environment"]["BUZZ_S3_BUCKET"])
        self.assertEqual(services["relay"]["environment"]["BUZZ_S3_BUCKET"], "${BUZZ_S3_BUCKET:-buzz-media}")

if __name__ == "__main__":
    unittest.main()
