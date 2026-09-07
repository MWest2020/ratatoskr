# SPDX-License-Identifier: EUPL-1.2
"""Voeg een pubkey toe als lid van een kanaal — via de kanaaleigenaar-nsec uit SOPS.

Kleine, auditeerbare tegenhanger van de add-member-stap in create-session-identity:
geen inline geheim-extractie op de shell (die tript de classifier), maar één script
dat de nsec uit secrets/identities.yaml haalt en `buzz channels add-member` draait.

  python3 orchestrator/add-member.py --chan escalatie --name odin-worker

--chan/--name lossen kanaal en identiteit op uit channels.yml/identities.yml, dus
je hoeft geen UUID of pubkey te plakken (die breken in een terminal over meerdere
regels, en dan faalt het commando stil-verkeerd).

--role default 'member' (een sessie is een deelnemer, geen listener-bot).
--owner default 'orchestrator': kanaalbeheer tekent als agent, niet als de mens
(zie change reown-channels-to-orchestrator). Voor een kanaal dat nog mens-owned
is: IDENT=mark ervoor, tot reown-channels.py gedraaid heeft.
"""
import argparse
import json
import os
import subprocess
import sys

import yaml

BOOMHUIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELAY = os.environ.get("BUZZ_RELAY_URL", "ws://192.168.178.60:3000")


def _resolve_channel(name):
    """Kanaal-UUID uit channels.yml op naam (kort commando i.p.v. lange UUID)."""
    doc = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml"))) or {}
    ch = (doc.get("channels") or {}).get(name)
    if not ch or "id" not in ch:
        sys.exit(f"[add-member] kanaal '{name}' niet in channels.yml.")
    return ch["id"]


def _resolve_pubkey(name):
    """Pubkey uit de PUBLIEKE identities.yml op identiteitsnaam."""
    doc = yaml.safe_load(open(os.path.join(BOOMHUIS, "identities.yml"))) or {}
    ident = (doc.get("identities") or {}).get(name)
    if not ident or "pubkey_hex" not in ident:
        sys.exit(f"[add-member] identiteit '{name}' niet in identities.yml.")
    return ident["pubkey_hex"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", help="kanaal-UUID (of gebruik --chan <naam>)")
    ap.add_argument("--chan", help="kanaalnaam uit channels.yml (kort)")
    ap.add_argument("--all-channels", action="store_true",
                    help="voeg toe aan ELK kanaal in channels.yml (idempotent)")
    ap.add_argument("--pubkey", help="pubkey_hex (of gebruik --name <identiteit>)")
    ap.add_argument("--name", help="identiteitsnaam uit identities.yml (kort)")
    ap.add_argument("--role", default="member", choices=["member", "bot"])
    ap.add_argument("--owner", default=os.environ.get("IDENT", "orchestrator"),
                    help="identiteit die het kanaal bezit (default orchestrator)")
    a = ap.parse_args()
    a.pubkey = a.pubkey or (_resolve_pubkey(a.name) if a.name else None)
    if not a.pubkey:
        sys.exit("[add-member] geef --pubkey/--name.")

    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    secp = os.path.join(BOOMHUIS, "secrets", "identities.yaml")
    dec = subprocess.run(["sops", "-d", secp], capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[add-member] SOPS-decrypt faalde: {dec.stderr[:200]}")
    ids = yaml.safe_load(dec.stdout)["identities"]
    if a.owner not in ids:
        sys.exit(f"[add-member] eigenaar '{a.owner}' niet in secret.")
    nsec = ids[a.owner]["nsec"]
    buzz = os.path.expanduser("~/.local/bin/buzz")
    benv = dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY)

    if a.all_channels:
        doc = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml"))) or {}
        targets = [(n, c["id"]) for n, c in (doc.get("channels") or {}).items() if "id" in c]
    else:
        cid = a.channel or (_resolve_channel(a.chan) if a.chan else None)
        if not cid:
            sys.exit("[add-member] geef --channel/--chan (of --all-channels).")
        targets = [(a.chan or cid, cid)]

    ok = 0
    for name, cid in targets:
        r = subprocess.run([buzz, "channels", "add-member", "--channel", cid,
                            "--pubkey", a.pubkey, "--role", a.role],
                           capture_output=True, text=True, env=benv)
        out = (r.stdout or "") + (r.stderr or "")
        try:
            accepted = bool(json.loads(r.stdout).get("accepted"))
        except (ValueError, AttributeError):
            accepted = False
        # 'al lid' is geen fout: idempotent doorgaan.
        if accepted or "already" in out.lower() or "member" in out.lower():
            ok += 1
            print(f"[add-member] #{name}: ok")
        else:
            print(f"[add-member] #{name}: OVERGESLAGEN ({out.strip()[:120]})")
    print(f"[add-member] {a.pubkey[:12]}… in {ok}/{len(targets)} kanalen als {a.role} (via {a.owner}).")


if __name__ == "__main__":
    main()
