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
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in requester)[:24]
    return f"session/{session_type}-{safe or 'unknown'}-{stamp}"


def _run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(" ".join(args[:3]) + ": " + (p.stderr or p.stdout).strip()[:200])
    return p.stdout


def install_hook(worktree, branch):
    """De hook in een EIGEN hooks-map van deze worktree zetten.

    Waarom niet gewoon `.git/hooks`: dat is de GEDEELDE map van de hele clone.
    Gemeten 2026-09-12, pijnlijk: de hook van een sessie blokkeerde daardoor mijn
    eigen push vanuit een andere worktree van dezelfde clone — "deze sessie mag
    alleen refs/heads/session/… pushen". Twee sessies zouden elkaars hook
    bovendien overschrijven.

    Git heeft hier een mechanisme voor: `extensions.worktreeConfig` zet
    `core.hooksPath` per worktree in plaats van voor de hele repo.
    """
    own = os.path.join(worktree, ".session-hooks")
    os.makedirs(own, exist_ok=True)
    _run(["git", "-C", worktree, "config", "extensions.worktreeConfig", "true"])
    _run(["git", "-C", worktree, "config", "--worktree", "core.hooksPath", own])
    path = os.path.join(own, "pre-push")
    with open(path, "w") as f:
        f.write(HOOK % branch)
    os.chmod(path, 0o755)
    # Niet meecommitten: het hek hoort bij de sessie, niet bij de branch. In een
    # worktree is `.git` een BESTAND, geen map — dus het pad opvragen aan git.
    exclude = _run(["git", "-C", worktree, "rev-parse", "--git-path",
                    "info/exclude"]).strip()
    if not os.path.isabs(exclude):
        exclude = os.path.join(worktree, exclude)
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    with open(exclude, "a") as f:
        f.write("\n.session-hooks/\n")
    return path


def create(repo, base_dir, session_type, requester, now=None):
    """(worktree, branch). Vers van `origin/main`, met het hek erin.

    `repo` is een bestaande clone; de worktree komt in `base_dir`, buiten elke
    draaiende checkout. Faalt er iets, dan gooit dit — een halve worktree is
    erger dan geen.
    """
    branch = branch_name(session_type, requester, now)
    target = os.path.join(base_dir, branch.replace("/", "-"))
    os.makedirs(base_dir, exist_ok=True)
    _run(["git", "-C", repo, "fetch", "--quiet", "origin", "main"])
    _run(["git", "-C", repo, "worktree", "add", "-q", "-b", branch, target, "origin/main"])
    install_hook(target, branch)
    return target, branch
