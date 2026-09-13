# SPDX-License-Identifier: EUPL-1.2
"""Tests for the VM-side push_subs helper (`orchestrator/vm/boomhuis-push-subs`).

The one thing worth a test here is ownership. The helper runs as root and the
file belongs to the chat; a prune that quietly takes the file over is invisible
until nobody gets a notification any more. That happened, so it gets a test.

Loaded by path because the script has no `.py` extension on purpose — it is
installed as a command, not imported.
"""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "vm", "boomhuis-push-subs")

_spec = importlib.util.spec_from_loader(
    "push_subs_helper", importlib.machinery.SourceFileLoader("push_subs_helper", SCRIPT))
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


class OwnershipStaysPut(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "push_subs.json")
        helper.PATHS = [self.path]

    def test_an_existing_file_keeps_its_owner_and_mode(self):
        with open(self.path, "w") as f:
            json.dump([{"endpoint": "https://a"}], f)
        os.chmod(self.path, 0o640)
        before = os.stat(self.path)

        helper._write([{"endpoint": "https://b"}])

        after = os.stat(self.path)
        self.assertEqual((after.st_uid, after.st_gid), (before.st_uid, before.st_gid))
        self.assertEqual(after.st_mode & 0o777, 0o640)
        self.assertEqual(json.load(open(self.path)), [{"endpoint": "https://b"}])

    def test_a_new_file_follows_the_directory(self):
        # The directory is the volume, and the volume belongs to the chat. A
        # fresh file that ignored it would be unreadable for the only process
        # that has to write to it.
        d = os.stat(self.dir)
        helper._write([])
        st = os.stat(self.path)
        self.assertEqual((st.st_uid, st.st_gid), (d.st_uid, d.st_gid))

    def test_prune_does_not_leave_a_stray_tmp_file(self):
        helper._write([{"endpoint": "https://a"}])
        self.assertEqual(os.listdir(self.dir), ["push_subs.json"])


class ReadingIsHonestAboutErrors(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "push_subs.json")
        helper.PATHS = [self.path]

    def test_no_file_means_no_subscribers(self):
        self.assertEqual(helper._read(), [])

    def test_an_unreadable_file_raises_instead_of_reporting_zero(self):
        # A false "0 subs" is worse than a crash: the sender then reports
        # success while nobody is reached.
        open(self.path, "w").write("[]")
        os.chmod(self.path, 0o000)
        if os.geteuid() == 0:
            self.skipTest("root reads everything; this test needs a normal user")
        with self.assertRaises(OSError):
            helper._read()


if __name__ == "__main__":
    unittest.main()
