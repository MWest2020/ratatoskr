# /// script
# dependencies = ["coincurve>=20", "bech32>=1.2", "pyyaml>=6"]
# ///
"""Maak een LICHTE relay-identiteit voor een vaste Claude-sessie.

Anders dan create-agent.py: GEEN handbook-def en GEEN listener-run-lijst — een
sessie is een interactieve Claude Code-sessie, geen door de listener gespawnde
chat-agent. Deze identiteit dient puur om berichten aan de echte afzender toe te
schrijven (identiteit = sleutelpaar), zodat ping.sh onder eigen sleutel post
i.p.v. onder 'bouwer'.

  uv run orchestrator/create-session-identity.py --name hubby

Doet: keypair → identities.yml (rol: sessie) → SOPS-nsec → relay-lid + #general-
lid → profielnaam. Idempotent-ish: bestaat de naam al, dan stopt 'ie.
"""
import argparse
import os
import subprocess
import sys
import time

from bech32 import bech32_encode, convertbits
from coincurve import PrivateKey
import yaml

BOOMHUIS = os.path.expanduser("~/boomhuis")
RELAY = "ws://192.168.178.60:3000"
GENERAL = "32ef5cd2-70d8-4b7e-9235-9692b8ab2a1c"


def run(cmd, env=None, inp=None):
    return subprocess.run(cmd, env=env, input=inp, capture_output=True, text=True)


def npub_nsec():
    pk = PrivateKey(os.urandom(32))
    pub = pk.public_key.format(compressed=True)[1:].hex()
    npub = bech32_encode("npub", convertbits(bytes.fromhex(pub), 8, 5))
    nsec = bech32_encode("nsec", convertbits(bytes.fromhex(pk.to_hex()), 8, 5))
    return pub, npub, pk.to_hex(), nsec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="sessienaam, bv. hubby")
    a = ap.parse_args()
    name = a.name.lower()
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    buzz = os.path.expanduser("~/.local/bin/buzz")

    idp = os.path.join(BOOMHUIS, "identities.yml")
    d = yaml.safe_load(open(idp))
    if name in d["identities"]:
        print(f"[session-id] '{name}' bestaat al in identities.yml — stop.")
        sys.exit(1)

    pub, npub, priv, nsec = npub_nsec()
    print(f"[session-id] {name}: npub={npub}")

    # 1) publieke registry
    d["identities"][name] = {"rol": "sessie", "status": "actief",
                             "pubkey_hex": pub, "npub": npub, "aangemaakt": "2026-09-02"}
    open(idp, "w").write("# Publieke identiteitsregistry van het boomhuis (spec: identity-registry).\n"
                         + yaml.safe_dump(d, default_flow_style=False, sort_keys=False))

    # 2) SOPS-nsec
    secp = os.path.join(BOOMHUIS, "secrets", "identities.yaml")
    sd = yaml.safe_load(run(["sops", "-d", secp], env=env).stdout)
    sd["identities"][name] = {"privkey_hex": priv, "nsec": nsec}
    tmp = os.path.join(BOOMHUIS, "secrets", "_new.yaml")
    with open(tmp, "w") as f:
        f.write("# Privesleutels van de boomhuis-identiteiten. Alleen SOPS+age-versleuteld in git.\n")
        yaml.safe_dump(sd, f, default_flow_style=False, sort_keys=False)
    run(["sops", "-e", "-i", tmp], env=env)
    os.replace(tmp, secp)

    # 3) relay-lid + #general-lid (als mark)
    mark_nsec = sd["identities"]["mark"]["nsec"]
    run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
         f"cd /opt/buzz-relay && docker compose exec -T relay buzz-admin add-member --pubkey {pub} --role member"])
    time.sleep(2)  # relay-lidmaatschap laten propageren
    benv = dict(os.environ, BUZZ_PRIVATE_KEY=mark_nsec, BUZZ_RELAY_URL=RELAY)
    r = run([buzz, "channels", "add-member", "--channel", GENERAL, "--pubkey", pub, "--role", "member"], env=benv)
    print(f"[session-id] #general-lid: {'ok' if 'accepted' in r.stdout and 'true' in r.stdout else r.stdout[:80] or r.stderr[:80]}")

    # 4) profielnaam
    run([buzz, "users", "set-profile", "--name", name, "--about", f"Claude-sessie {name}"],
        env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))

    print(f"[session-id] {name} klaar. ping.sh IDENT={name} post nu onder eigen sleutel.")
    print("VOLGENDE: commit identities.yml + secrets; de sessie kan pingen met "
          f"IDENT={name} ~/boomhuis/orchestrator/ping.sh '<bericht>'.")


if __name__ == "__main__":
    main()
