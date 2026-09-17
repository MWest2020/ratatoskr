# SPDX-License-Identifier: MIT
# /// script
# dependencies = ["coincurve>=20", "bech32>=1.2", "pyyaml>=6"]
# ///
"""Create a LIGHT relay identity for a standing Claude session.

Unlike create-agent.py: NO handbook def and NO listener run list — a session is
an interactive Claude Code session, not a chat agent spawned by the listener. The
identity exists purely to attribute messages to the real sender (identity = key
pair), so ping.sh posts under its own key.

  uv run orchestrator/create-session-identity.py --name hubby

Fail-closed: the plaintext secret goes into a gitignored temp file
(secrets/_*.yaml, mode 0600) that is always cleaned up; nothing is written to the
git-tracked secrets/identities.yaml until the SOPS output is verified encrypted.
The secret goes before the public registry entry, and the #escalatie membership
must succeed (otherwise exit != 0) — no half state.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

from bech32 import bech32_encode, convertbits
from coincurve import PrivateKey
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BOOMHUIS = os.path.dirname(HERE)  # orchestrator/ sits in the repo root
RELAY = "ws://192.168.178.60:3000"


def run(cmd, env=None, inp=None):
    return subprocess.run(cmd, env=env, input=inp, capture_output=True, text=True)


def report_channel_id():
    """#escalatie, not #general: #general is odin's hub channel and a session may
    not post there (ping.sh refuses it). A session reports in the project channel,
    and in #escalatie when Mark has to decide — so that is the one membership
    every session needs."""
    return yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml")))["channels"]["escalatie"]["id"]


def npub_nsec():
    pk = PrivateKey(os.urandom(32))
    pub = pk.public_key.format(compressed=True)[1:].hex()
    npub = bech32_encode("npub", convertbits(bytes.fromhex(pub), 8, 5))
    nsec = bech32_encode("nsec", convertbits(bytes.fromhex(pk.to_hex()), 8, 5))
    return pub, npub, pk.to_hex(), nsec


def store_secret(secp, sd, env):
    """Add the new secret and write back fail-closed: plaintext only in a
    gitignored temp (0600), and only replaced after verified encryption."""
    tmp = os.path.join(BOOMHUIS, "secrets", "_new.yaml")  # gitignored (secrets/_*.yaml)
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("# Privesleutels van de boomhuis-identiteiten. Alleen SOPS+age-versleuteld in git.\n")
            yaml.safe_dump(sd, f, default_flow_style=False, sort_keys=False)
        enc = run(["sops", "-e", "-i", tmp], env=env)
        if enc.returncode != 0 or "sops:" not in open(tmp).read():
            sys.exit(f"[session-id] SOPS-encrypt faalde of output niet versleuteld — "
                     f"NIETS weggeschreven (geen plaintext naar git). {enc.stderr[:160]}")
        os.replace(tmp, secp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="session name, e.g. hubby")
    a = ap.parse_args()
    name = a.name.lower()
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    buzz = os.path.expanduser("~/.local/bin/buzz")
    report_chan = report_channel_id()

    idp = os.path.join(BOOMHUIS, "identities.yml")
    d = yaml.safe_load(open(idp))
    if name in d["identities"]:
        sys.exit(f"[session-id] '{name}' bestaat al in identities.yml — stop.")

    pub, npub, priv, nsec = npub_nsec()
    print(f"[session-id] {name}: npub={npub}")

    # 1) SOPS secret FIRST (fail-closed)
    secp = os.path.join(BOOMHUIS, "secrets", "identities.yaml")
    dec = run(["sops", "-d", secp], env=env)
    if dec.returncode != 0:
        sys.exit(f"[session-id] SOPS-decrypt faalde: {dec.stderr[:200]}")
    sd = yaml.safe_load(dec.stdout)
    sd["identities"][name] = {"privkey_hex": priv, "nsec": nsec}
    store_secret(secp, sd, env)

    # 2) public registry (only after the secret)
    d["identities"][name] = {"rol": "sessie", "status": "actief", "pubkey_hex": pub,
                             "npub": npub, "aangemaakt": datetime.date.today().isoformat()}
    open(idp, "w").write("# Publieke identiteitsregistry van het boomhuis (spec: identity-registry).\n"
                         + yaml.safe_dump(d, default_flow_style=False, sort_keys=False))

    # 3) relay member + #escalatie member (as mark); return codes checked.
    mark_nsec = sd["identities"]["mark"]["nsec"]
    rm = run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
              f"cd /opt/buzz-relay && docker compose exec -T relay buzz-admin add-member --pubkey {pub} --role member"])
    if rm.returncode != 0:
        print(f"[session-id] WAARSCHUWING: relay add-member faalde: {(rm.stderr or rm.stdout)[:160]}")
    time.sleep(2)  # let relay membership propagate
    benv = dict(os.environ, BUZZ_PRIVATE_KEY=mark_nsec, BUZZ_RELAY_URL=RELAY)
    # --role member (not 'bot'): a session is a participant, not a listener bot.
    r = run([buzz, "channels", "add-member", "--channel", report_chan, "--pubkey", pub, "--role", "member"], env=benv)
    ok = False
    if r.returncode == 0:
        try:
            ok = bool(json.loads(r.stdout).get("accepted"))
        except (ValueError, AttributeError):
            ok = False
    if not ok:
        sys.exit(f"[session-id] #escalatie-lidmaatschap MISLUKT: {(r.stdout or r.stderr)[:160]} — "
                 "registry/secret staan al, maar de identiteit kan nog niet posten; check de relay.")
    print("[session-id] #escalatie-lid: ok")

    # 4) profile name
    run([buzz, "users", "set-profile", "--name", name, "--about", f"Claude-sessie {name}"],
        env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))
    print(f"[session-id] {name} klaar. De sessie post met "
          f"IDENT={name} ~/boomhuis/orchestrator/ping.sh '<bericht>'.")


if __name__ == "__main__":
    main()
