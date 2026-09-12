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
        name = work_tree.branch_name("build", "mark", now=1700000000)
        self.assertEqual(name, "session/build-mark-1700000000")

    def test_strange_requester_is_made_safe(self):
        """Een naam belandt in een branchnaam én in een pad."""
        name = work_tree.branch_name("build", "../../etc/passwd", now=1)
        self.assertNotIn("/", name.split("session/", 1)[1])
        self.assertNotIn("..", name)

    def test_empty_requester_still_yields_a_name(self):
        self.assertIn("unknown", work_tree.branch_name("build", "", now=1))


class Hook(unittest.TestCase):
    """De hook krijgt van git op stdin: "<local> <sha> <remote> <sha>"."""

    def _hook(self, branch="session/build-mark-1"):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "pre-push")
        with open(path, "w") as f:
            f.write(work_tree.HOOK % branch)
        os.chmod(path, 0o755)
        return path

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
        top = tempfile.mkdtemp()
        origin = os.path.join(top, "origin")
        os.makedirs(origin)
        _git(["init", "-q", "-b", "main"], origin)
        open(os.path.join(origin, "f.txt"), "w").write("x")
        _git(["add", "-A"], origin)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], origin)
        clone = os.path.join(top, "clone")
        _git(["clone", "-q", origin, clone], top)
        return top, clone

    def test_worktree_is_fresh_and_fenced(self):
        top, clone = self._repo()
        work, branch = work_tree.create(clone, os.path.join(top, "sessions"),
                                        "build", "mark", now=42)
        self.assertTrue(os.path.isfile(os.path.join(work, "f.txt")))
        # Buiten de clone: een sessie mag niet in een draaiende checkout schrijven.
        self.assertFalse(work.startswith(clone))
        self.assertEqual(branch, "session/build-mark-42")
        current = _git(["rev-parse", "--abbrev-ref", "HEAD"], work).stdout.strip()
        self.assertEqual(current, branch)
        # En het hek staat er, uitvoerbaar.
        hooks = _git(["rev-parse", "--git-path", "hooks"], work).stdout.strip()
        path = hooks if os.path.isabs(hooks) else os.path.join(work, hooks)
        self.assertTrue(os.access(os.path.join(path, "pre-push"), os.X_OK))

    def test_hook_does_not_leak_to_the_rest_of_the_clone(self):
        """Gemeten 2026-09-12: de hook stond in de GEDEELDE .git/hooks en
        blokkeerde daarmee pushes vanuit elke andere worktree van dezelfde clone.
        Het hek hoort bij de sessie, niet bij de repo."""
        top, clone = self._repo()
        work, _ = work_tree.create(clone, os.path.join(top, "sessions"),
                                   "build", "mark", now=42)
        shared = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"],
                      work).stdout.strip()
        self.assertFalse(os.path.exists(os.path.join(shared, "hooks", "pre-push")),
                         "de hook mag niet in de gedeelde hooks-map staan")
        # En de worktree gebruikt wél zijn eigen map.
        own = _git(["config", "core.hooksPath"], work).stdout.strip()
        self.assertTrue(own.endswith(".session-hooks"), own)
        self.assertTrue(os.access(os.path.join(own, "pre-push"), os.X_OK))

    def test_hook_dir_is_not_committed(self):
        top, clone = self._repo()
        work, _ = work_tree.create(clone, os.path.join(top, "sessions"),
                                   "build", "mark", now=42)
        out = _git(["status", "--porcelain"], work).stdout
        self.assertNotIn(".session-hooks", out)

    def test_missing_repo_raises_instead_of_half_a_worktree(self):
        with self.assertRaises(Exception):
            work_tree.create("/bestaat/niet", tempfile.mkdtemp(), "build", "mark")


if __name__ == "__main__":
    unittest.main()
