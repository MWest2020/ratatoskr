# SPDX-License-Identifier: EUPL-1.2
"""Draag het eigenaarschap van mens-owned kanalen over aan de orchestrator.

Waarom: de web-chat tekende kanaal-aanmaak als `mark` (de mens), dus die kanalen
zijn mens-owned. Alleen een eigenaar mag een kanaal beheren (beschrijving, topic,
delete), en geautomatiseerd kanaalbeheer met marks mens-sleutel is
impersonatie-adjacent. Zie change `reown-channels-to-orchestrator`.

Dit is de ENIGE plek waar marks sleutel gebruikt mag worden, en uitsluitend voor
`channels add-member --role owner` — nooit om te posten. Eenmalig te draaien; na
`fix-channels-create-as-orchestrator` ontstaan er geen nieuwe mens-owned kanalen
meer. Idempotent: een kanaal dat de orchestrator al bezit wordt overgeslagen.

    SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt python3 orchestrator/reown-channels.py [--dry-run]
"""
import json
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BOOMHUIS = os.path.dirname(HERE)
RELAY = os.environ.get("BUZZ_RELAY_URL", "ws://192.168.178.60:3000")
BUZZ = os.path.expanduser("~/.local/bin/buzz")


def _identities():
    env = dict(os.environ,
               SOPS_AGE_KEY_FILE=os.environ.get(
                   "SOPS_AGE_KEY_FILE", os.path.expanduser("~/.config/sops/age/keys.txt")))
    dec = subprocess.run(["sops", "-d", os.path.join(BOOMHUIS, "secrets", "identities.yaml")],
                         capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[reown] SOPS-decrypt faalde: {dec.stderr[:200]}")
    return yaml.safe_load(dec.stdout)["identities"]


def _buzz(args, nsec):
    return subprocess.run([BUZZ, *args], capture_output=True, text=True,
                          env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))


def _owner_of(cid, nsec):
    """pubkey_hex van de eigenaar, of None als de ledenlijst niet leesbaar is."""
    p = _buzz(["channels", "members", "--channel", cid], nsec)
    if p.returncode != 0:
        return None
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return None
    members = d if isinstance(d, list) else d.get("members", [])
    return next((m.get("pubkey") for m in members if m.get("role") == "owner"), None)


def main():
    dry = "--dry-run" in sys.argv
    pub = yaml.safe_load(open(os.path.join(BOOMHUIS, "identities.yml")))["identities"]
    chans = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml")))["channels"]
    orch, mark = pub["orchestrator"]["pubkey_hex"], pub["mark"]["pubkey_hex"]
    secrets = _identities()

    failed = []
    for name, c in chans.items():
        cid = c.get("id")
        if not cid:
            continue
        owner = _owner_of(cid, secrets["orchestrator"]["nsec"])
        if owner == orch:
            print(f"[reown] #{name}: al orchestrator-owned")
            continue
        if owner != mark:
            print(f"[reown] #{name}: eigenaar {str(owner)[:8]} — niet mark, overgeslagen")
            continue
        if dry:
            print(f"[reown] #{name}: ZOU overdragen mark -> orchestrator")
            continue
        # Alleen hier marks sleutel, en alleen voor deze ene rolwijziging.
        p = _buzz(["channels", "add-member", "--channel", cid,
                   "--pubkey", orch, "--role", "owner"], secrets["mark"]["nsec"])
        if p.returncode != 0:
            failed.append((name, (p.stderr or p.stdout).strip()[:160]))
            print(f"[reown] #{name}: FOUT — {failed[-1][1]}")
            continue
        now = _owner_of(cid, secrets["orchestrator"]["nsec"])
        ok = now == orch
        print(f"[reown] #{name}: overgedragen -> {'orchestrator' if ok else str(now)[:8]}")
        if not ok:
            failed.append((name, "rol niet doorgevoerd op de relay"))

    if failed:
        sys.exit(f"[reown] {len(failed)} kanaal(en) niet overgedragen: "
                 + ", ".join(n for n, _ in failed))
    print("[reown] klaar — alle kanalen orchestrator-owned")


if __name__ == "__main__":
    main()
