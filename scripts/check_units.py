#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Do the systemd units installed on this host match the ones in the repository?

Why this exists: on 2026-09-12 the board timer in git said two minutes while the
installed unit still said ten. The repository was right, the machine was not, and
nothing noticed — Mark did, from the app: "building lane update niet".

Units are code that lives in two places, and that is exactly the kind of thing
that drifts unnoticed. This compares them.

    python3 scripts/check_units.py            # report, non-zero on drift
    python3 scripts/check_units.py --install  # copy the repo's version over
"""
import argparse
import filecmp
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INSTALLED = os.path.expanduser("~/.config/systemd/user")
SOURCES = ("jobs/systemd", "agents/systemd", "orchestrator/systemd")


# Units die hier draaien en bewust niet in deze repo staan, mét de reden en de
# repo waar ze wél thuishoren.
#
# Een kale allowlist zou hier ook werken en is een slechter idee: over een half
# jaar weet niemand meer of een naam er nog hoort te staan, en dan blijft hij
# staan. Een uitzondering die zegt waaróm is toezicht; een uitzondering zonder
# reden is een blinde vlek met een net pak aan.
ELDERS = {
    "zettelkast-daily.service": "hoort bij MWest2020/zettelkast",
    "zettelkast-daily.timer": "hoort bij MWest2020/zettelkast",
}

# Wat wij beheren. Alles daarbuiten op deze machine gaat ons niet aan, en erover
# klagen maakt de gate ruis — waarna iemand hem uitzet.
VAN_ONS = ("ratatoskr-", "claude-", "boomhuis-", "zettelkast-")


def host_units(installed=None):
    """De unit-bestanden die op deze host geïnstalleerd staan en van ons zijn."""
    map_ = INSTALLED if installed is None else installed
    if not os.path.isdir(map_):
        return []
    return sorted(n for n in os.listdir(map_)
                  if n.startswith(VAN_ONS)
                  and os.path.isfile(os.path.join(map_, n)))


def alleen_op_de_host(repo_namen, host_namen, elders=None):
    """Units die hier draaien en nergens in git staan.

    Dit is de richting die ontbrak. `check_units` vergeleek alleen repo -> host:
    voor elke unit in de repo, staat hij ook op de machine. Een unit die ALLEEN
    op de host bestaat is daarmee per constructie onzichtbaar — de gate meet
    precies de verzameling waar het gat niet in zit.

    Gemeten op 2026-09-16: `claude-secret-refresh.{service,timer}` draaide hier
    al maanden, stond nergens in git, en faalde 82 keer op rij zonder dat enige
    gate iets zei.
    """
    bekend = ELDERS if elders is None else elders
    return [(n, bekend.get(n)) for n in host_namen if n not in repo_namen]


def repo_units():
    out = {}
    for d in SOURCES:
        for path in glob.glob(os.path.join(ROOT, d, "*")):
            if os.path.isfile(path):
                out[os.path.basename(path)] = path
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true",
                    help="copy the repo's version over and reload systemd")
    a = ap.parse_args()

    drift, missing = [], []
    for naam, bron in sorted(repo_units().items()):
        doel = os.path.join(INSTALLED, naam)
        if not os.path.exists(doel):
            missing.append(naam)
        elif not filecmp.cmp(bron, doel, shallow=False):
            drift.append(naam)
        if a.install and (naam in drift or naam in missing):
            os.makedirs(INSTALLED, exist_ok=True)
            shutil.copy2(bron, doel)

    # De andere kant op: wat draait hier dat nergens in git staat?
    vreemd = alleen_op_de_host(set(repo_units()), host_units())
    onbekend = [n for n, reden in vreemd if reden is None]

    if a.install:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        print(f"units: {len(drift)} bijgewerkt, {len(missing)} geïnstalleerd")
        print("vergeet niet: systemctl --user restart <timer> voor wat al liep")
        return 0

    for naam in missing:
        print(f"  NIET GEINSTALLEERD  {naam}")
    for naam in drift:
        print(f"  AFGEDREVEN          {naam}  (repo != host)")
    for naam, reden in vreemd:
        if reden:
            print(f"  ELDERS              {naam}  ({reden})")
        else:
            print(f"  NIET IN GIT         {naam}  (draait hier, staat nergens)")
    if drift or missing or onbekend:
        print(f"\nunits: {len(drift)} afgedreven, {len(missing)} niet geïnstalleerd,"
              f" {len(onbekend)} niet in git")
        if drift or missing:
            print("  afgedreven/ontbrekend: `python3 scripts/check_units.py --install`")
        if onbekend:
            print("  niet in git: zet hem in */systemd/ of geef hem een reden in"
                  " ELDERS — laten staan is de derde optie, en de slechtste")
        return 1
    print("units: groen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
