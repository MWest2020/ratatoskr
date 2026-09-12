# SPDX-License-Identifier: EUPL-1.2
"""Tests voor de worktree van een schrijvende sessie — vooral voor het hek.

Het hek is het hele punt: een schrijvende sessie krijgt `Bash`, en dan is "push
niet naar main" in een prompt niets waard. Deze tests draaien de hook ECHT, met
de invoer die git hem geeft, want een hook die niet doet wat je denkt is erger
dan geen hook.
"""
import os
import subprocess
import tempfile
import unittest

import work_tree


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


class BranchName(unittest.TestCase):
    def test_shape(self):
        naam = work_tree.branch_name("build", "mark", now=1700000000)
        self.assertEqual(naam, "session/build-mark-1700000000")

    def test_strange_requester_is_made_safe(self):
        """Een naam belandt in een branchnaam én in een pad."""
        naam = work_tree.branch_name("build", "../../etc/passwd", now=1)
        self.assertNotIn("/", naam.split("session/", 1)[1])
        self.assertNotIn("..", naam)

    def test_empty_requester_still_yields_a_name(self):
        self.assertIn("unknown", work_tree.branch_name("build", "", now=1))


class Hook(unittest.TestCase):
    """De hook krijgt van git op stdin: "<local> <sha> <remote> <sha>"."""

    def _hook(self, branch="session/build-mark-1"):
        d = tempfile.mkdtemp()
        pad = os.path.join(d, "pre-push")
        with open(pad, "w") as f:
            f.write(work_tree.HOOK % branch)
        os.chmod(pad, 0o755)
        return pad

    def _push(self, hook, remote_ref):
        return subprocess.run([hook], input=f"refs/heads/x abc {remote_ref} def\n",
                              capture_output=True, text=True)

    def test_main_is_refused(self):
        p = self._push(self._hook(), "refs/heads/main")
        self.assertEqual(p.returncode, 1)
        self.assertIn("geweigerd", p.stderr)

    def test_own_branch_passes(self):
        p = self._push(self._hook(), "refs/heads/session/build-mark-1")
        self.assertEqual(p.returncode, 0)

    def test_another_branch_is_refused(self):
        """Ook een onschuldige andere branch: alleen de eigen branch mag."""
        p = self._push(self._hook(), "refs/heads/werk/iets-anders")
        self.assertEqual(p.returncode, 1)

    def test_delete_of_main_is_refused(self):
        """Een verwijder-push heeft een lege lokale ref maar wél een remote ref."""
        p = subprocess.run([self._hook()], input="(delete) 0000 refs/heads/main 0000\n",
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)


class Create(unittest.TestCase):
    def _repo(self):
        """Een clone met een `origin/main`, zoals de echte situatie."""
        boven = tempfile.mkdtemp()
        oorsprong = os.path.join(boven, "origin")
        os.makedirs(oorsprong)
        _git(["init", "-q", "-b", "main"], oorsprong)
        open(os.path.join(oorsprong, "f.txt"), "w").write("x")
        _git(["add", "-A"], oorsprong)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], oorsprong)
        clone = os.path.join(boven, "clone")
        _git(["clone", "-q", oorsprong, clone], boven)
        return boven, clone

    def test_worktree_is_fresh_and_fenced(self):
        boven, clone = self._repo()
        werk, branch = work_tree.create(clone, os.path.join(boven, "sessies"),
                                        "build", "mark", now=42)
        self.assertTrue(os.path.isfile(os.path.join(werk, "f.txt")))
        # Buiten de clone: een sessie mag niet in een draaiende checkout schrijven.
        self.assertFalse(werk.startswith(clone))
        self.assertEqual(branch, "session/build-mark-42")
        huidige = _git(["rev-parse", "--abbrev-ref", "HEAD"], werk).stdout.strip()
        self.assertEqual(huidige, branch)
        # En het hek staat er, uitvoerbaar.
        hooks = _git(["rev-parse", "--git-path", "hooks"], werk).stdout.strip()
        pad = hooks if os.path.isabs(hooks) else os.path.join(werk, hooks)
        self.assertTrue(os.access(os.path.join(pad, "pre-push"), os.X_OK))

    def test_missing_repo_raises_instead_of_half_a_worktree(self):
        with self.assertRaises(Exception):
            work_tree.create("/bestaat/niet", tempfile.mkdtemp(), "build", "mark")


if __name__ == "__main__":
    unittest.main()
