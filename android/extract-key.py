#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Haal de ondertekensleutel uit SOPS en zet 'm als bestand neer.

De keystore staat versleuteld in `secrets/android-signing.yaml` omdat Android de
IDENTITEIT van een app aan die sleutel ontleent: kwijt betekent een ándere app,
en iedereen moet opnieuw installeren. Hij hoort dus bij de repo, niet bij een
machine.

    python3 android/extract-key.py /tmp/ks

Ruim die map daarna op. Dit script schrijft niets in de repo en drukt het
wachtwoord niet af — het zet het in een bestand naast de keystore, 0600.
"""
import base64
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main(argv):
    if len(argv) < 2:
        raise SystemExit("gebruik: extract-key.py <doelmap>")
    target = argv[1]
    os.environ.setdefault("SOPS_AGE_KEY_FILE",
                          os.path.expanduser("~/.config/sops/age/keys.txt"))
    p = subprocess.run(["sops", "-d", os.path.join(ROOT, "secrets", "android-signing.yaml")],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("sops faalde: " + (p.stderr or "").strip()[:200])
    d = yaml.safe_load(p.stdout)["android"]

    os.makedirs(target, exist_ok=True)
    os.chmod(target, 0o700)
    ks = os.path.join(target, "ratatoskr.keystore")
    with open(ks, "wb") as f:
        f.write(base64.b64decode(d["keystore_base64"]))
    os.chmod(ks, 0o600)
    pw = os.path.join(target, "password.txt")
    with open(pw, "w") as f:
        f.write(d["wachtwoord"] + "\n")
    os.chmod(pw, 0o600)

    print(ks)
    print("alias:", d["alias"])
    print("vingerafdruk:", d["vingerafdruk_sha256"])
    print("wachtwoord staat in:", pw)


if __name__ == "__main__":
    main(sys.argv)
