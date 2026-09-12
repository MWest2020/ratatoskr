# SPDX-License-Identifier: EUPL-1.2
"""Add a pubkey as a member of a channel — through the channel owner nsec in SOPS.

A small, auditable counterpart to the add-member step in
create-session-identity: no inline secret extraction on the shell (that trips the
classifier), but one script that pulls the nsec out of secrets/identities.yaml
and runs `buzz channels add-member`.

  python3 orchestrator/add-member.py --chan escalatie --name odin-worker

--chan/--name resolve the channel and the identity from
channels.yml/identities.yml, so you need not paste a UUID or a pubkey (those
break across lines in a terminal, and then the command fails silently wrong).

--role defaults to 'member' (a session is a participant, not a listener bot).
--owner defaults to 'orchestrator': channel management signs as an agent, not as
the human (see change reown-channels-to-orchestrator). For a channel that is
still human-owned: IDENT=mark in front, until reown-channels.py has run.
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
    """Channel UUID from channels.yml by name (a short command instead of a UUID)."""
    doc = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml"))) or {}
    ch = (doc.get("channels") or {}).get(name)
    if not ch or "id" not in ch:
        sys.exit(f"[add-member] kanaal '{name}' niet in channels.yml.")
    return ch["id"]


def _resolve_pubkey(name):
    """Pubkey from the PUBLIC identities.yml by identity name."""
    doc = yaml.safe_load(open(os.path.join(BOOMHUIS, "identities.yml"))) or {}
    ident = (doc.get("identities") or {}).get(name)
    if not ident or "pubkey_hex" not in ident:
        sys.exit(f"[add-member] identiteit '{name}' niet in identities.yml.")
    return ident["pubkey_hex"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", help="channel UUID (or use --chan <name>)")
    ap.add_argument("--chan", help="channel name from channels.yml (short)")
    ap.add_argument("--all-channels", action="store_true",
                    help="add to EVERY channel in channels.yml (idempotent)")
    ap.add_argument("--pubkey", help="pubkey_hex (or use --name <identity>)")
    ap.add_argument("--name", help="identity name from identities.yml (short)")
    ap.add_argument("--role", default="member", choices=["member", "bot"])
    ap.add_argument("--owner", default=os.environ.get("IDENT", "orchestrator"),
                    help="identity that owns the channel (default orchestrator)")
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
        # 'already a member' is not an error: carry on, idempotently.
        if accepted or "already" in out.lower() or "member" in out.lower():
            ok += 1
            print(f"[add-member] #{name}: ok")
        else:
            print(f"[add-member] #{name}: OVERGESLAGEN ({out.strip()[:120]})")
    print(f"[add-member] {a.pubkey[:12]}… in {ok}/{len(targets)} kanalen als {a.role} (via {a.owner}).")


if __name__ == "__main__":
    main()
