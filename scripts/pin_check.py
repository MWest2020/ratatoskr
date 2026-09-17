#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Controleer dat alles wat we uitrollen gepind is.

"Immutable images" stond in CLAUDE.md en werd niet gehandhaafd: het
compose-bestand viel terug op `:main`, en de workflow gebruikte `@v4`. Een pin
die niemand controleert is een voornemen.

Drie regels:
  1. Elk `image:` in deploy/ is letterlijk — geen ${VAR}, geen `:-fallback` —
     en draagt minstens major.minor, een sha-tag of een digest.
  2. Elke `uses:` in .github/workflows is op een commit-SHA gepind.
  3. BUZZ_REF in chat/Dockerfile hoort bij dezelfde upstream-commit als de
     relay-tag in het compose-bestand.

    python3 scripts/pin_check.py
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

IMAGE = re.compile(r"^\s*image:\s*(\S+)", re.M)
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.M)
# major.minor (17.6-alpine), een sha-tag (sha-4baccd5) of een digest.
GOED = re.compile(r":(?:sha-[0-9a-f]{7,}|\d+\.\d+[\w.\-]*)$|@sha256:[0-9a-f]{64}$")


def check_images():
    fouten = []
    for pad in glob.glob(os.path.join(ROOT, "deploy", "*.yml")):
        for ref in IMAGE.findall(open(pad).read()):
            naam = os.path.relpath(pad, ROOT)
            if "${" in ref:
                fouten.append(f"{naam}: image uit een variabele ({ref}) — zet 'm letterlijk")
            elif not GOED.search(ref):
                fouten.append(f"{naam}: {ref} is niet specifiek genoeg "
                              f"(minstens major.minor, een sha-tag of een digest)")
    return fouten


def check_actions():
    fouten = []
    for pad in glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml")):
        for ref in USES.findall(open(pad).read()):
            if "@" not in ref:
                continue
            sha = ref.rsplit("@", 1)[1]
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                fouten.append(f"{os.path.relpath(pad, ROOT)}: {ref} is niet op een "
                              f"commit-SHA gepind")
    return fouten


def check_buzz_ref():
    """De CLI in het chat-image komt uit dezelfde upstream-commit als de relay."""
    try:
        dockerfile = open(os.path.join(ROOT, "chat", "Dockerfile")).read()
        compose = open(os.path.join(ROOT, "deploy", "docker-compose.yml")).read()
    except OSError as e:
        return [f"kan de pinbestanden niet lezen: {e}"]
    m = re.search(r"ARG BUZZ_REF=([0-9a-f]{7,})", dockerfile)
    r = re.search(r"image:\s*ghcr\.io/block/buzz:sha-([0-9a-f]{7,})", compose)
    if not m or not r:
        return ["BUZZ_REF of de relay-tag niet gevonden — pin-controle onmogelijk"]
    if not m.group(1).startswith(r.group(1)):
        return [f"BUZZ_REF ({m.group(1)[:12]}) hoort niet bij de relay-tag "
                f"(sha-{r.group(1)}) — CLI en relay lopen uiteen"]
    return []


def main():
    fouten = check_images() + check_actions() + check_buzz_ref()
    for f in fouten:
        print("  NIET GEPIND  " + f)
    if fouten:
        print(f"\npins: {len(fouten)} probleem/problemen")
        return 1
    print("pins: groen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
