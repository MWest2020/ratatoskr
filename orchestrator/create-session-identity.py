# SPDX-License-Identifier: MIT
# /// script
# dependencies = ["coincurve>=20", "bech32>=1.2", "pyyaml>=6"]
# ///
"""Create a LIGHT relay identity for a standing Claude session.

Unlike the factory: NO handbook def and NO listener run list — a session is an
interactive Claude Code session, not a chat agent spawned by the listener. The
identity exists purely to attribute messages to the real sender (identity = key
pair), so ping.sh posts under its own key.

Two phases:

  # an agent, in a worktree, in its PR (the default phase):
  uv run orchestrator/create-session-identity.py --name heimdall --display Heimdall \
      --about "the coding session on agent-lxc" --chan statistics
  # Mark, after the merge; the orchestrator key signs:
  uv run orchestrator/create-session-identity.py --name heimdall --chan statistics \
      --phase relay --owner-step

Fail-closed: the plaintext secret goes into a gitignored temp file
(secrets/_*.yaml, mode 0600) that is always cleaned up; nothing is written to the
git-tracked secrets/identities.yaml until the SOPS output is verified encrypted.
The secret goes before the public registry entry, and every channel membership
must succeed (otherwise exit != 0) — no half state.

Channel changes are signed by the orchestrator, the channel owner, like the
factory; never by the human identity (until 2026-11-24 this script signed them
as Mark). The checks live in session_identity.py. They are not the gate: the
permission layer and Mark running the owner step are.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

import yaml

import session_identity as si

HERE = os.path.dirname(os.path.abspath(__file__))
BOOMHUIS = os.path.dirname(HERE)  # orchestrator/ sits in the repo root
RELAY = "ws://192.168.178.60:3000"
BUZZ = os.path.expanduser("~/.local/bin/buzz")
ENV = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))


def run(cmd, env=None, inp=None):
    return subprocess.run(cmd, env=env, input=inp, capture_output=True, text=True)


def npub_nsec():
    from bech32 import bech32_encode, convertbits
    from coincurve import PrivateKey
    pk = PrivateKey(os.urandom(32))
    pub = pk.public_key.format(compressed=True)[1:].hex()
    npub = bech32_encode("npub", convertbits(bytes.fromhex(pub), 8, 5))
    nsec = bech32_encode("nsec", convertbits(bytes.fromhex(pk.to_hex()), 8, 5))
    return pub, npub, pk.to_hex(), nsec


def derive(entry):
    """The pubkey the SOPS entry really belongs to; None if nsec and
    privkey_hex disagree or do not parse."""
    from bech32 import bech32_decode, convertbits
    from coincurve import PrivateKey
    try:
        hrp, data = bech32_decode(entry["nsec"])
        if hrp != "nsec" or bytes(convertbits(data, 5, 8, False)).hex() != entry["privkey_hex"]:
            return None
        pk = PrivateKey(bytes.fromhex(entry["privkey_hex"]))
        return pk.public_key.format(compressed=True)[1:].hex()
    except (TypeError, ValueError, KeyError):
        return None


def decrypt(secp):
    dec = run(["sops", "-d", secp], env=ENV)
    if dec.returncode != 0:
        sys.exit(f"[session-id] SOPS-decrypt faalde: {dec.stderr[:200]}")
    return yaml.safe_load(dec.stdout)


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


def parse(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="session name, e.g. heimdall")
    ap.add_argument("--display", help="display name, e.g. Heimdall (default: --name)")
    ap.add_argument("--about", help="one line: what this session is")
    ap.add_argument("--chan", action="append", default=[],
                    help="extra channel from channels.yml (repeatable); #escalatie always")
    ap.add_argument("--phase", choices=si.PHASES, default="registry",
                    help="registry (default): key + registry entry, for a PR. relay: relay "
                         "and channel membership. all: both. relay/all are Mark's step")
    ap.add_argument("--owner-step", action="store_true",
                    help="required for relay/all: Mark runs it, the orchestrator key signs")
    return ap.parse_args(argv)


def create(name, display, about, d, sd, idp, secp):
    if name in d["identities"] or name in sd["identities"]:
        sys.exit(f"[session-id] '{name}' bestaat al — stop.")
    pub, npub, priv, nsec = npub_nsec()
    print(f"[session-id] {name}: npub={npub}")
    sd["identities"][name] = {"privkey_hex": priv, "nsec": nsec}  # 1) secret FIRST
    store_secret(secp, sd, ENV)
    d["identities"][name] = {"rol": "sessie", "status": "actief", "pubkey_hex": pub,  # 2) registry
                             "npub": npub, "aangemaakt": datetime.date.today().isoformat(),
                             "display_name": display, "about": about}
    open(idp, "w").write("# Publieke identiteitsregistry van het boomhuis (spec: identity-registry).\n"
                         + yaml.safe_dump(d, default_flow_style=False, sort_keys=False))


def main(argv=None):
    a = parse(argv)
    try:
        name = si.check_name(a.name)
        phase = si.check_phase(a.phase, a.owner_step)
        chans = si.channel_ids(a.chan, yaml.safe_load(
            open(os.path.join(BOOMHUIS, "channels.yml")))["channels"])
    except si.Refused as e:
        sys.exit(f"[session-id] {e}")
    idp = os.path.join(BOOMHUIS, "identities.yml")
    secp = os.path.join(BOOMHUIS, "secrets", "identities.yaml")
    d, sd = yaml.safe_load(open(idp)), decrypt(secp)
    if phase != "relay":
        create(name, a.display or name, a.about or f"Claude session {name}", d, sd, idp, secp)
    if phase == "registry":
        extra = "".join(f" --chan {c}" for c, _ in chans[1:])
        print(f"[session-id] {name}: key + registry written; commit them in a PR. Then Mark's "
              f"step (the orchestrator key signs):\n  uv run orchestrator/create-session-identity.py"
              f" --name {name}{extra} --phase relay --owner-step")
        return
    print("[session-id] owner step: Mark runs this; the orchestrator key signs.")
    try:
        pub, nsec = si.relay_target(name, d["identities"], sd["identities"], derive)
    except si.Refused as e:
        sys.exit(f"[session-id] {e}")
    e = d["identities"][name]
    display, about = a.display or e.get("display_name", name), a.about or e.get("about", "")

    # 3) relay member + channel member (signed by the orchestrator); codes checked.
    rm = run(["ssh", "-o", "BatchMode=yes", "buzz-relay", "sudo", "-n", "docker", "exec",
              "buzz-prod-relay-1", "buzz-admin", "add-member", "--pubkey", pub, "--role", "member"])
    if rm.returncode != 0:
        print(f"[session-id] WARNING: relay add-member failed: {(rm.stderr or rm.stdout)[:160]}")
    time.sleep(2)  # let relay membership propagate
    benv = dict(os.environ, BUZZ_PRIVATE_KEY=sd["identities"]["orchestrator"]["nsec"], BUZZ_RELAY_URL=RELAY)
    for cname, cid in chans:
        # --role member (not 'bot'): a session is a participant, not a listener bot.
        r = run([BUZZ, "channels", "add-member", "--channel", cid, "--pubkey", pub,
                 "--role", "member"], env=benv)
        try:
            ok = r.returncode == 0 and bool(json.loads(r.stdout).get("accepted"))
        except (ValueError, AttributeError):
            ok = False
        if not ok:
            sys.exit(f"[session-id] #{cname} membership FAILED: {(r.stdout or r.stderr)[:160]} — "
                     "the identity cannot post there yet; rerun this owner step.")
        print(f"[session-id] #{cname} member: ok")

    # 4) profile name, signed by the session's own key
    run([BUZZ, "users", "set-profile", "--name", display, "--about", about[:120]],
        env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))
    print(f"[session-id] {name} done. The session posts with "
          f"IDENT={name} CHAN=escalatie ~/ratatoskr/orchestrator/ping.sh '<message>'.")


if __name__ == "__main__":
    main()
