# SPDX-License-Identifier: EUPL-1.2
"""Zet de native kanaal-beschrijving op elk relay-kanaal vanuit channels.yml `doel`.

Reproduceerbaar (i.p.v. een eenmalige handmatige `buzz channels update`): draai dit
opnieuw als een `doel` in channels.yml wijzigt of na een relay-herstel. Alleen de
eigenaar mag een kanaal updaten, dus we proberen orchestrator en dan mark.

  uv run orchestrator/set-channel-descriptions.py   (of: python3, met pyyaml)
"""
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BOOMHUIS = os.path.dirname(HERE)
RELAY = os.environ.get("BUZZ_RELAY_URL", "ws://192.168.178.60:3000")
BUZZ = os.path.expanduser("~/.local/bin/buzz")


def sops_secret(name):
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    dec = subprocess.run(["sops", "-d", os.path.join(BOOMHUIS, "secrets", "identities.yaml")],
                         capture_output=True, text=True, env=env)
    return yaml.safe_load(dec.stdout)["identities"][name]["nsec"]


def main():
    chans = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml")))["channels"]
    owners = {"orchestrator": sops_secret("orchestrator"), "mark": sops_secret("mark")}
    for name, c in chans.items():
        cid, doel = c.get("id"), (c.get("doel") or "")[:200]
        if not cid or not doel:
            print(f"  #{name}: overgeslagen (geen id/doel)"); continue
        done = False
        for who, nsec in owners.items():
            env = dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY)
            r = subprocess.run([BUZZ, "channels", "update", "--channel", cid, "--description", doel],
                               capture_output=True, text=True, env=env)
            if r.returncode == 0 and "error" not in r.stdout.lower():
                print(f"  #{name}: beschrijving gezet (als {who})"); done = True; break
        if not done:
            print(f"  #{name}: MISLUKT — {(r.stdout or r.stderr)[:80]}", file=sys.stderr)


if __name__ == "__main__":
    main()
