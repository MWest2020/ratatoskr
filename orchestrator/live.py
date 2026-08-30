#!/usr/bin/env python3
"""Genereer knowledge/_live.md — 'wat er nu draait', als context voor de coordinator.

Bronnen: de draaiende chat-agents (agents.yml), open handover-batons
(handover/*.md met status != afgehandeld/gearchiveerd) en — als een cluster is
gekoppeld (env KUBECTL gezet) — de habitat-Jobs. Zonder cluster: expliciet
gemeld, zodat de coordinator niet doet alsof hij het weet. Draai periodiek
(systemd-timer) of on-demand.
"""
import glob
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


def main():
    L = ["# Wat er nu draait (gegenereerd — niet handmatig bewerken)", ""]
    L += ["## Draaiende chat-agents (listener)"]
    L += [f"- @{h}" for h in chat_agents()]
    L += ["", "## Open handover-batons"]
    batons = open_batons()
    L += [f"- {n} — {o}. Volgende: {nx}" for n, o, nx in batons] or ["- (geen open batons)"]
    L += ["", "## Habitat-Jobs"]
    j = habitat_jobs()
    L += [j] if j else ["- (cluster niet gekoppeld — env KUBECTL niet gezet)"]
    open(os.path.join(ROOT, "knowledge", "_live.md"), "w").write("\n".join(L) + "\n")
    print("knowledge/_live.md geschreven")


if __name__ == "__main__":
    main()
