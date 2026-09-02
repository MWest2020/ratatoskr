# SPDX-License-Identifier: EUPL-1.2
# /// script
# dependencies = ["coincurve>=20", "bech32>=1.2", "pyyaml>=6"]
# ///
"""Maak een LICHTE relay-identiteit voor een vaste Claude-sessie.

Anders dan create-agent.py: GEEN handbook-def en GEEN listener-run-lijst — een
sessie is een interactieve Claude Code-sessie, geen door de listener gespawnde
chat-agent. De identiteit dient puur om berichten aan de echte afzender toe te
schrijven (identiteit = sleutelpaar), zodat ping.sh onder eigen sleutel post.

  uv run orchestrator/create-session-identity.py --name hubby

Fail-closed: de plaintext-secret komt in een gitignored temp (secrets/_*.yaml,
mode 0600) die altijd wordt opgeruimd; er wordt pas naar het git-getrackte
secrets/identities.yaml geschreven als de SOPS-output geverifieerd versleuteld is.
De secret gaat vóór de publieke registry-entry, en het #general-lidmaatschap moet
lukken (anders exit != 0) — geen halve staat.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time

from bech32 import bech32_encode, convertbits
from coincurve import PrivateKey
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BOOMHUIS = os.path.dirname(HERE)  # orchestrator/ zit in de repo-root
RELAY = "ws://192.168.178.60:3000"


def run(cmd, env=None, inp=None):
    return subprocess.run(cmd, env=env, input=inp, capture_output=True, text=True)


def general_id():
    return yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml")))["channels"]["general"]["id"]


def npub_nsec():
    pk = PrivateKey(os.urandom(32))
    pub = pk.public_key.format(compressed=True)[1:].hex()
    npub = bech32_encode("npub", convertbits(bytes.fromhex(pub), 8, 5))
    nsec = bech32_encode("nsec", convertbits(bytes.fromhex(pk.to_hex()), 8, 5))
    return pub, npub, pk.to_hex(), nsec


def store_secret(secp, sd, env):
    """Voeg de nieuwe secret toe en schrijf fail-closed terug: plaintext alleen in
    een gitignored temp (0600), en pas vervangen na geverifieerde encryptie."""
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
    ap.add_argument("--name", required=True, help="sessienaam, bv. hubby")
    a = ap.parse_args()
    name = a.name.lower()
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    buzz = os.path.expanduser("~/.local/bin/buzz")
    general = general_id()

    idp = os.path.join(BOOMHUIS, "identities.yml")
    d = yaml.safe_load(open(idp))
    if name in d["identities"]:
        sys.exit(f"[session-id] '{name}' bestaat al in identities.yml — stop.")

    pub, npub, priv, nsec = npub_nsec()
    print(f"[session-id] {name}: npub={npub}")

    # 1) SOPS-secret EERST (fail-closed)
    secp = os.path.join(BOOMHUIS, "secrets", "identities.yaml")
    dec = run(["sops", "-d", secp], env=env)
    if dec.returncode != 0:
        sys.exit(f"[session-id] SOPS-decrypt faalde: {dec.stderr[:200]}")
    sd = yaml.safe_load(dec.stdout)
    sd["identities"][name] = {"privkey_hex": priv, "nsec": nsec}
    store_secret(secp, sd, env)

    # 2) publieke registry (pas ná de secret)
    d["identities"][name] = {"rol": "sessie", "status": "actief", "pubkey_hex": pub,
                             "npub": npub, "aangemaakt": datetime.date.today().isoformat()}
    open(idp, "w").write("# Publieke identiteitsregistry van het boomhuis (spec: identity-registry).\n"
                         + yaml.safe_dump(d, default_flow_style=False, sort_keys=False))

    # 3) relay-lid + #general-lid (als mark); returncodes gecheckt.
    mark_nsec = sd["identities"]["mark"]["nsec"]
    rm = run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
              f"cd /opt/buzz-relay && docker compose exec -T relay buzz-admin add-member --pubkey {pub} --role member"])
    if rm.returncode != 0:
        print(f"[session-id] WAARSCHUWING: relay add-member faalde: {(rm.stderr or rm.stdout)[:160]}")
    time.sleep(2)  # relay-lidmaatschap laten propageren
    benv = dict(os.environ, BUZZ_PRIVATE_KEY=mark_nsec, BUZZ_RELAY_URL=RELAY)
    # --role member (niet 'bot'): een sessie is een deelnemer, geen listener-bot.
    r = run([buzz, "channels", "add-member", "--channel", general, "--pubkey", pub, "--role", "member"], env=benv)
    if not ("accepted" in r.stdout and "true" in r.stdout):
        sys.exit(f"[session-id] #general-lidmaatschap MISLUKT: {(r.stdout or r.stderr)[:160]} — "
                 "registry/secret staan al, maar de identiteit kan nog niet posten; check de relay.")
    print("[session-id] #general-lid: ok")

    # 4) profielnaam
    run([buzz, "users", "set-profile", "--name", name, "--about", f"Claude-sessie {name}"],
        env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))
    print(f"[session-id] {name} klaar. De sessie post met "
          f"IDENT={name} ~/boomhuis/orchestrator/ping.sh '<bericht>'.")


if __name__ == "__main__":
    main()
