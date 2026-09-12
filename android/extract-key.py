#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Pull the signing key out of SOPS and put it down as a file.

The keystore is encrypted in `secrets/android-signing.yaml` because Android
derives the IDENTITY of an app from that key: lose it and it is a different app,
and everyone has to reinstall. So it belongs with the repo, not with a machine.

    python3 android/extract-key.py /tmp/ks

Clean that directory up afterwards. This script writes nothing into the repo and
does not print the password — it puts it in a file next to the keystore, 0600.
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
        raise SystemExit("usage: extract-key.py <target dir>")
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
    print("fingerprint:", d["vingerafdruk_sha256"])
    print("password is in:", pw)


if __name__ == "__main__":
    main(sys.argv)
