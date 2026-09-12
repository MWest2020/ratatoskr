#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
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

    if a.install:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        print(f"units: {len(drift)} bijgewerkt, {len(missing)} geïnstalleerd")
        print("vergeet niet: systemctl --user restart <timer> voor wat al liep")
        return 0

    for naam in missing:
        print(f"  NIET GEINSTALLEERD  {naam}")
    for naam in drift:
        print(f"  AFGEDREVEN          {naam}  (repo != host)")
    if drift or missing:
        print(f"\nunits: {len(drift)} afgedreven, {len(missing)} niet geïnstalleerd"
              f" — `python3 scripts/check_units.py --install`")
        return 1
    print("units: groen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
