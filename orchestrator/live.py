#!/usr/bin/env python3
"""Genereer knowledge/_live.md — 'wat er nu draait', als context voor de coordinator.

Bronnen: de draaiende chat-agents (agents.yml), open handover-batons
(handover/*.md met status != afgehandeld/gearchiveerd) en — als een cluster is
gekoppeld (env KUBECTL gezet) — de habitat-Jobs. Zonder cluster: expliciet
gemeld, zodat de coordinator niet doet alsof hij het weet. Draai periodiek
(systemd-timer) of on-demand.
"""
import glob
import subprocess
import os
import re
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chat_agents():
    d = yaml.safe_load(open(os.path.join(ROOT, "agents", "agents.yml")))
    return d.get("run", [])


def open_batons():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "handover", "*.md"))):
        s = open(p).read()
        m = re.match(r"^---\n(.*?)\n---", s, re.S)
        fm = yaml.safe_load(m.group(1)) if m else {}
        status = str(fm.get("status", ""))
        if "afgehandeld" in status or "gearchiveerd" in status:
            continue
        out.append((os.path.basename(p),
                    fm.get("onderwerp") or status or "",
                    fm.get("next_step", "")))
    return out


def open_changes():
    """OpenSpec-changes op propose (niet gearchiveerd) = open werk."""
    d = os.path.join(ROOT, "openspec", "changes")
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d)
                  if n != "archive" and os.path.isdir(os.path.join(d, n)))


def open_prs():
    """Open PR's op boomhuis via gh (leeg als gh faalt/ontbreekt)."""
    try:
        r = subprocess.run(["gh", "pr", "list", "--repo", "MWest2020/boomhuis",
                            "--state", "open", "--json", "number,title"],
                           capture_output=True, text=True, timeout=20)
        import json as _json
        return [(p["number"], p["title"]) for p in _json.loads(r.stdout or "[]")]
    except Exception:
        return []


def habitat_jobs():
    """Habitat-Jobs (namespace 'agents'), alleen als een cluster is gekoppeld via
    env KUBECTL (bv. 'ssh jumpy kubectl'). HABITAT_NS overschrijft de namespace."""
    kubectl = os.environ.get("KUBECTL")
    if not kubectl:
        return None
    ns = os.environ.get("HABITAT_NS", "agents")
    try:
        r = subprocess.run(kubectl.split() + ["get", "jobs", "-n", ns, "--no-headers"],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or f"(geen jobs in ns {ns})"
    except Exception as e:
        return f"(kubectl-fout: {e})"


def checkout_state():
    """Waar komt dit bestand vandaan? Een liveness-bestand dat uit een achterlopende
    of vuile werkkopie komt, meldt werk dat niet bestaat en agents die niet draaien.
    Dat gebeurde: `~/boomhuis` stond 52 commits achter met ongecommitte
    wijzigingen, en `_live.md` toonde daardoor @archivaris als draaiend en een
    change als open die allang gearchiveerd was. Geen `git fetch` hier — dit draait
    op een timer; we vergelijken met wat de checkout al van origin weet."""
    def git(*a):
        try:
            return subprocess.run(["git", "-C", ROOT, *a], capture_output=True,
                                  text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    sha = git("rev-parse", "--short", "HEAD") or "?"
    behind = git("rev-list", "--count", "HEAD..origin/main") or "?"
    dirty = len([r for r in git("status", "--porcelain").splitlines() if r.strip()])
    line = f"_bron: {branch}@{sha}"
    warnings = []
    if branch != "main":
        warnings.append(f"niet op main ({branch})")
    if behind not in ("0", "?"):
        warnings.append(f"{behind} commits achter origin/main")
    if dirty:
        warnings.append(f"{dirty} ongecommitte wijziging(en)")
    if warnings:
        return ("> ⚠ **Dit overzicht komt uit een afwijkende werkkopie**: "
                + ", ".join(warnings)
                + ". Wat hier staat kan werk melden dat niet bestaat, of agents "
                  "die niet draaien.\n", line + " — AFWIJKEND_")
    return ("", line + "_")


def main():
    warning, source = checkout_state()
    L = ["# Wat er nu draait (gegenereerd — niet handmatig bewerken)", ""]
    if warning:
        L += [warning]
    L += ["## Draaiende chat-agents (listener)"]
    L += [f"- @{h}" for h in chat_agents()]
    L += ["", "## Open werk (backlog — altijd oppakken)"]
    L += ["### OpenSpec-changes op propose"]
    L += [f"- {n}" for n in open_changes()] or ["- (geen)"]
    prs = open_prs()
    L += ["### Open PR's"]
    L += [f"- #{n} {t}" for n, t in prs] or ["- (geen)"]
    L += ["", "## Open handover-batons"]
    batons = open_batons()
    L += [f"- {n} — {o}. Volgende: {nx}" for n, o, nx in batons] or ["- (geen open batons)"]
    L += ["", "## Habitat-Jobs"]
    j = habitat_jobs()
    L += [j] if j else ["- (cluster niet gekoppeld — env KUBECTL niet gezet)"]
    L += ["", source]
    open(os.path.join(ROOT, "knowledge", "_live.md"), "w").write("\n".join(L) + "\n")
    print("knowledge/_live.md geschreven")


if __name__ == "__main__":
    main()
