# SPDX-License-Identifier: EUPL-1.2
"""Zet de native kanaal-beschrijving op elk relay-kanaal vanuit channels.yml `doel`.

Reproduceerbaar (i.p.v. een eenmalige handmatige `buzz channels update`): draai dit
opnieuw als een `doel` in channels.yml wijzigt of na een relay-herstel.

Tekent UITSLUITEND met de orchestrator-sleutel (een agent), nooit met marks
mens-sleutel. Kanalen die door de mens zijn aangemaakt (chat-backend maakt ze nu
nog als `mark`) kan de orchestrator niet updaten → die worden gemeld als
"her-eigenaarschap nodig" (zie de follow-up-change reown-channels-to-orchestrator).
Exit != 0 als er iets niet gezet kon worden.
"""
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BOOMHUIS = os.path.dirname(HERE)
RELAY = os.environ.get("BUZZ_RELAY_URL", "ws://192.168.178.60:3000")
BUZZ = os.path.expanduser("~/.local/bin/buzz")


def orchestrator_nsec():
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    dec = subprocess.run(["sops", "-d", os.path.join(BOOMHUIS, "secrets", "identities.yaml")],
                         capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[set-desc] SOPS-decrypt faalde: {dec.stderr[:200]}")
    return yaml.safe_load(dec.stdout)["identities"]["orchestrator"]["nsec"]


def main():
    chans = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml")))["channels"]
    env = dict(os.environ, BUZZ_PRIVATE_KEY=orchestrator_nsec(), BUZZ_RELAY_URL=RELAY)
    failed = []
    for name, c in chans.items():
        cid, purpose = c.get("id"), (c.get("doel") or "").strip()
        if not cid or not purpose:
            print(f"  #{name}: overgeslagen (geen id/doel)"); continue
        r = subprocess.run([BUZZ, "channels", "update", "--channel", cid, "--description", purpose[:200]],
                           capture_output=True, text=True, env=env)
        if r.returncode == 0 and '"error"' not in r.stdout:
            print(f"  #{name}: beschrijving gezet")
        else:
            print(f"  #{name}: NIET gezet — {(r.stdout or r.stderr)[:80]}")
            failed.append(name)
    if failed:
        sys.exit(f"[set-desc] {len(failed)} kanaal/kanalen niet gezet: {', '.join(failed)} "
                 "(waarschijnlijk mens-owned; zie follow-up reown-channels-to-orchestrator).")
    print("[set-desc] alle beschrijvingen gezet.")


if __name__ == "__main__":
    main()
