# SPDX-License-Identifier: EUPL-1.2
"""Een verse git-worktree voor een schrijvende werksessie, met een hek erin.

Waarom een eigen worktree: `~/ratatoskr-listener` draait de listener en de chat
draait uit een image. Een sessie die in een draaiende checkout schrijft, verbouwt
zichzelf tijdens het werk. Er draaiden ooit twee listeners omdat een herstart uit
twee verschillende bomen kwam — dat soort verwarring wil je niet ook nog per
sessie.

Waarom een pre-push-hook en niet een zin in de prompt: een schrijvende sessie
krijgt `Bash` (anders geen git en geen tests), en dan is "push niet naar main" in
een prompt niets waard. Alles wat in zijn context komt — een README, een issue,
een opgehaalde pagina — kan die instructie sturen. Een hook kan dat niet.

Engels in de code per ADR-0001; deze module is nieuw.
"""
import os
import subprocess
import time

# Het hek. `git push` geeft elke ref op stdin door als "<local> <sha> <remote> <sha>";
# alles wat niet naar de eigen branch gaat, weigeren we. Ook `main` expliciet,
# zodat de melding duidelijk is in plaats van een generieke afwijzing.
HOOK = """#!/bin/sh
# Geschreven door agents/work_tree.py. Een schrijvende werksessie mag alleen zijn
# EIGEN branch pushen: zo blijft een pull request de enige uitkomst.
allowed="refs/heads/%s"
while read -r _local _lsha remote _rsha; do
    [ -z "$remote" ] && continue
    if [ "$remote" != "$allowed" ]; then
        echo "pre-push: geweigerd — deze sessie mag alleen $allowed pushen," >&2
        echo "          niet $remote. Open een pull request." >&2
        exit 1
    fi
done
exit 0
"""


def branch_name(session_type, requester, now=None):
    """Herkenbaar en uniek: type, wie erom vroeg, wanneer."""
    stamp = int(now or time.time())
    veilig = "".join(c if c.isalnum() or c in "-_" else "-" for c in requester)[:24]
    return f"session/{session_type}-{veilig or 'unknown'}-{stamp}"


def _run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(" ".join(args[:3]) + ": " + (p.stderr or p.stdout).strip()[:200])
    return p.stdout


def install_hook(worktree, branch):
    """De hook in de worktree zetten. Een worktree heeft geen eigen .git-map maar
    een .git-BESTAND dat naar de administratie wijst; de hooks staan daar."""
    gitdir = _run(["git", "-C", worktree, "rev-parse", "--git-path", "hooks"]).strip()
    hooks = gitdir if os.path.isabs(gitdir) else os.path.join(worktree, gitdir)
    os.makedirs(hooks, exist_ok=True)
    pad = os.path.join(hooks, "pre-push")
    with open(pad, "w") as f:
        f.write(HOOK % branch)
    os.chmod(pad, 0o755)
    return pad


def create(repo, base_dir, session_type, requester, now=None):
    """(worktree, branch). Vers van `origin/main`, met het hek erin.

    `repo` is een bestaande clone; de worktree komt in `base_dir`, buiten elke
    draaiende checkout. Faalt er iets, dan gooit dit — een halve worktree is
    erger dan geen.
    """
    branch = branch_name(session_type, requester, now)
    doel = os.path.join(base_dir, branch.replace("/", "-"))
    os.makedirs(base_dir, exist_ok=True)
    _run(["git", "-C", repo, "fetch", "--quiet", "origin", "main"])
    _run(["git", "-C", repo, "worktree", "add", "-q", "-b", branch, doel, "origin/main"])
    install_hook(doel, branch)
    return doel, branch
