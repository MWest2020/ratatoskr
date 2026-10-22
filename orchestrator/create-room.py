# SPDX-License-Identifier: MIT
"""Create a shared room (openspec change shared-room): a private channel owned
by the orchestrator, with the human and the room's agents as members.

    python3 orchestrator/create-room.py --name werkplaats --members architect,bouwer,reviewer

The owner runs this, not an agent: adding members is channel management, and the
auto-mode classifier refuses it to agents (docs/how-to/ping-from-a-session.md).
It prints the channel id; the room becomes active once that id and a `room:`
block are in channels.yml and the listener has restarted.

Idempotent on the members ("already a member" is fine). It refuses to create a
second channel with the same name.
"""
import argparse
import json
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELAY = os.environ.get("BUZZ_RELAY_URL", "ws://192.168.178.60:3000")
BUZZ = os.path.expanduser("~/.local/bin/buzz")


def owner_env(owner):
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    dec = subprocess.run(["sops", "-d", os.path.join(ROOT, "secrets", "identities.yaml")],
                         capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[create-room] SOPS decrypt failed: {dec.stderr[:200]}")
    ids = yaml.safe_load(dec.stdout)["identities"]
    if owner not in ids:
        sys.exit(f"[create-room] owner '{owner}' is not in the secret.")
    return dict(os.environ, BUZZ_PRIVATE_KEY=ids[owner]["nsec"], BUZZ_RELAY_URL=RELAY)


def buzz(args, env):
    r = subprocess.run([BUZZ, *args], capture_output=True, text=True, env=env, timeout=30)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def existing(name, env):
    """The id of a visible channel with exactly this name, or None."""
    code, out, _ = buzz(["channels", "list"], env)
    if code != 0:
        return None
    try:
        rows = json.loads(out)
    except ValueError:
        return None
    rows = rows if isinstance(rows, list) else rows.get("channels", [])
    # The relay calls it `channel_id` in a listing (measured 2026-10-22).
    return next((c.get("channel_id") or c.get("id") for c in rows
                 if c.get("name") == name), None)


def pubkey(name):
    ids = (yaml.safe_load(open(os.path.join(ROOT, "identities.yml"))) or {})["identities"]
    if name not in ids or "pubkey_hex" not in ids[name]:
        sys.exit(f"[create-room] identity '{name}' is not in identities.yml.")
    return ids[name]["pubkey_hex"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--members", required=True, help="agent handles, comma-separated")
    ap.add_argument("--human", default="mark")
    ap.add_argument("--owner", default="orchestrator")
    a = ap.parse_args()
    env = owner_env(a.owner)
    cid = existing(a.name, env)
    if cid:
        print(f"[create-room] #{a.name} exists already: {cid}")
    else:
        code, out, err = buzz(["channels", "create", "--name", a.name, "--type", "stream",
                               "--visibility", "private", "--description",
                               "Shared room: agents pick up work by contract; every "
                               "piece of work is a GitHub issue."], env)
        if code != 0:
            sys.exit(f"[create-room] create failed: {(err or out)[:200]}")
        try:
            d = json.loads(out)
            cid = d.get("channel_id") or d.get("id")
        except ValueError:
            cid = None
        cid = cid or existing(a.name, env)
        if not cid:
            sys.exit(f"[create-room] created, but no id in the answer: {out[:200]}")
        print(f"[create-room] #{a.name} created: {cid}")
    for who in [a.human] + [m.strip() for m in a.members.split(",") if m.strip()]:
        code, out, err = buzz(["channels", "add-member", "--channel", cid,
                               "--pubkey", pubkey(who), "--role", "member"], env)
        text = (out + err).lower()
        ok = code == 0 or "already" in text
        print(f"[create-room] {who}: {'ok' if ok else 'FAILED ' + (err or out)[:120]}")
    print(f"\nchannels.yml:\n  {a.name}:\n    id: {cid}")


if __name__ == "__main__":
    main()
