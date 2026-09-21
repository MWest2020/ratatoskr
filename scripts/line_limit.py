#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Handhaaf de regelgrens van 200. Zonder handhaving is een conventie een wens.

De grens staat al maanden in AGENTS.md en werd al maanden overschreden — dat is
precies wat er gebeurt met een regel die niemand controleert.

    python3 scripts/line_limit.py            # rapporteer + faal bij overtreding
    python3 scripts/line_limit.py --baseline # schrijf de huidige stand als baseline

De baseline bevat wat er bij invoering al te lang was. Die lijst mag alleen
korter worden: een bestand dat erop staat en groeit, faalt alsnog. Leeg vóór het
archiveren van de change.
"""
import argparse
import os
import subprocess
import sys

LIMIT = 200
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASELINE = os.path.join(HERE, "line_limit_baseline.txt")

# Wat telt als code. Markdown, YAML en JSON niet: die zijn proza of data, en
# "splits je config op" is geen verbetering.
EXTENSIONS = (".py", ".js", ".sh", ".css", ".html")
NAMES = ("Dockerfile",)

# Uitzonderingen, elk met een reden. Geen categorie zonder reden.
EXEMPT = {
    "deploy/docker-compose.yml": "vendored upstream-config; splitsen breekt de herkomst",
}


def tracked_files():
    """Alles wat git zou meenemen: gevolgd ÉN nieuw-maar-niet-genegeerd.

    Alleen `ls-files` kijkt naar wat al gevolgd wordt, en dus precies niet naar
    een nieuw bestand — het moment waarop de kans op een overtreding het grootst
    is. Gemeten 2026-09-13: `orchestrator/test_push_chain.py` was 231 regels,
    lokaal groen omdat hij nog untracked was, en rood in CI zodra hij gecommit
    was. Een poort die pas dichtgaat nadat je gepusht hebt is een poort die je
    leert om CI te gebruiken als linter.
    """
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "--cached", "--others",
                          "--exclude-standard"], capture_output=True,
                         text=True, check=True).stdout.split()
    return [f for f in out
            if (f.endswith(EXTENSIONS) or os.path.basename(f) in NAMES)
            and f not in EXEMPT]


def count(path):
    try:
        with open(os.path.join(ROOT, path), errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def over_limit():
    return {f: n for f in tracked_files() if (n := count(f)) > LIMIT}


def load_baseline():
    """{pad: regels} van wat bij invoering al te lang was."""
    try:
        with open(BASELINE) as f:
            rows = [r.split(None, 1) for r in f if r.strip() and not r.startswith("#")]
        return {pad.strip(): int(n) for n, pad in rows}
    except OSError:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true",
                    help="schrijf de huidige overschrijdingen als baseline")
    a = ap.parse_args()
    te_lang = over_limit()

    if a.baseline:
        with open(BASELINE, "w") as f:
            f.write("# Bestanden die bij invoering van de regelgrens al te lang waren.\n"
                    "# Deze lijst mag alleen KORTER worden; groeien = alsnog rood.\n")
            for pad, n in sorted(te_lang.items()):
                f.write(f"{n} {pad}\n")
        print(f"baseline geschreven: {len(te_lang)} bestanden")
        return 0

    basis = load_baseline()
    nieuw = {f: n for f, n in te_lang.items() if f not in basis}
    gegroeid = {f: (n, basis[f]) for f, n in te_lang.items()
                if f in basis and n > basis[f]}

    for f, n in sorted(nieuw.items()):
        print(f"  TE LANG  {n:>4}  {f}")
    for f, (n, was) in sorted(gegroeid.items()):
        print(f"  GEGROEID {n:>4}  {f}  (baseline {was})")

    rest = len(basis)
    if nieuw or gegroeid:
        print(f"\nregelgrens {LIMIT}: {len(nieuw)} nieuw te lang, "
              f"{len(gegroeid)} gegroeid boven de baseline")
        return 1
    print(f"regelgrens {LIMIT}: groen"
          + (f" ({rest} op de baseline, die moet nog naar nul)" if rest else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
