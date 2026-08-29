# /// script
# dependencies = ["coincurve>=20", "bech32>=1.2", "pyyaml>=6"]
# ///
"""Maak een nieuwe chat-agent aan — automatiseert de volledige dans.

Na een coordinator-voorstel dat Mark goedkeurt:
  uv run orchestrator/create-agent.py --name ontwerper --channels general,architectuur \
      --mandaat "Sparringpartner voor frontend/UX en design-systemen." \
      --system "Je bent 'ontwerper', ... Kort, Nederlands."

Doet: keypair genereren → handbook-def op een BRANCH + PR (CODEOWNERS = Mark) →
boomhuis identities.yml + secrets (SOPS) → relay- en kanaal-bot-lid → run-lijst.
De agent gaat pas LIVE nadat Mark de handbook-PR merget (guardrail: de listener
leest de def van main) en de listener herstart.
"""
import argparse
import os
import subprocess
import sys

from bech32 import bech32_encode, convertbits
from coincurve import PrivateKey
import yaml

HANDBOOK = os.path.expanduser("~/handbook")
BOOMHUIS = os.path.expanduser("~/boomhuis")
RELAY = "ws://192.168.178.60:3000"
GENERAL = "32ef5cd2-70d8-4b7e-9235-9692b8ab2a1c"


def run(cmd, cwd=None, env=None, inp=None):
    return subprocess.run(cmd, cwd=cwd, env=env, input=inp, capture_output=True, text=True)


def npub_nsec():
    pk = PrivateKey(os.urandom(32))
    pub = pk.public_key.format(compressed=True)[1:].hex()
    npub = bech32_encode("npub", convertbits(bytes.fromhex(pub), 8, 5))
    nsec = bech32_encode("nsec", convertbits(bytes.fromhex(pk.to_hex()), 8, 5))
    return pub, npub, pk.to_hex(), nsec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--channels", required=True, help="komma-gescheiden, bv. general,architectuur")
    ap.add_argument("--mandaat", required=True)
    ap.add_argument("--system", required=True, help="chat-facet systemprompt")
    a = ap.parse_args()
    name = a.name.lower()
    chans = [c.strip() for c in a.channels.split(",") if c.strip()]
    pub, npub, priv, nsec = npub_nsec()
    print(f"[create] {name}: npub={npub}")

    # 1) handbook-def op een branch + PR
    br = f"add-agent-{name}"
    run(["git", "checkout", "-q", "main"], cwd=HANDBOOK)
    run(["git", "checkout", "-q", "-b", br], cwd=HANDBOOK)
    doc = f"""---
status: actief
last_reviewed: 2026-08-29
agent:
  naam: {name}
  npub: {npub}
  chat:
    channels: [{', '.join(chans)}]
  executie: null
---

# {name}

## Mandaat

{a.mandaat}

## Chat-facet (boomhuis)

> {a.system}

Kanaal-scope: {', '.join('#'+c for c in chans)}.

## Executie-facet

Geen — {name} draait alleen in de chat.
"""
    path = os.path.join(HANDBOOK, "docs", "agents", f"{name}.md")
    open(path, "w").write(doc)
    run(["git", "add", path], cwd=HANDBOOK)
    run(["git", "commit", "-q", "-m", f"agent-registry: {name} (via coordinator/create-agent)"], cwd=HANDBOOK)
    run(["git", "push", "-q", "-u", "origin", br], cwd=HANDBOOK)
    pr = run(["gh", "pr", "create", "--repo", "MWest2020/handbook", "--head", br,
              "--title", f"Nieuwe agent: {name}", "--body",
              f"Canonieke def voor @{name}. Kanalen: {', '.join(chans)}.\n\nMandaat: {a.mandaat}\n\n"
              "Aangemaakt via de coordinator-flow (create-agent). Merge activeert de agent "
              "(de listener leest de def van main)."], cwd=HANDBOOK)
    run(["git", "checkout", "-q", "main"], cwd=HANDBOOK)
    print(f"[create] handbook-PR: {pr.stdout.strip() or pr.stderr.strip()}")

    # 2) boomhuis identities.yml + secrets
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    idp = os.path.join(BOOMHUIS, "identities.yml")
    d = yaml.safe_load(open(idp))
    d["identities"][name] = {"rol": "chat-agent", "status": "actief",
                             "pubkey_hex": pub, "npub": npub, "aangemaakt": "2026-08-29"}
    open(idp, "w").write("# Publieke identiteitsregistry van het boomhuis (spec: identity-registry).\n"
                         + yaml.safe_dump(d, default_flow_style=False, sort_keys=False))
    secp = os.path.join(BOOMHUIS, "secrets", "identities.yaml")
    plain = run(["sops", "-d", secp], env=env).stdout
    sd = yaml.safe_load(plain)
    sd["identities"][name] = {"privkey_hex": priv, "nsec": nsec}
    tmp = os.path.join(BOOMHUIS, "secrets", "_new.yaml")
    with open(tmp, "w") as f:
        f.write("# Privesleutels van de boomhuis-identiteiten. Alleen SOPS+age-versleuteld in git.\n")
        yaml.safe_dump(sd, f, default_flow_style=False, sort_keys=False)
    run(["sops", "-e", "-i", tmp], env=env)
    os.replace(tmp, secp)

    # 3) run-lijst
    ap_ = os.path.join(BOOMHUIS, "agents", "agents.yml")
    rd = yaml.safe_load(open(ap_))
    if name not in rd["run"]:
        rd["run"].append(name)
    head = open(ap_).read().split("run:")[0]
    open(ap_, "w").write(head + "run:\n" + "".join(f"  - {h}\n" for h in rd["run"]))

    # 4) relay- en kanaal-bot-lid (als mark)
    mark_nsec = next(v["nsec"] for k, v in sd["identities"].items() if k == "mark")
    run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
         f"cd /opt/buzz-relay && docker compose exec -T relay buzz-admin add-member --pubkey {pub} --role member"])
    benv = dict(os.environ, BUZZ_PRIVATE_KEY=mark_nsec, BUZZ_RELAY_URL=RELAY)
    buzz = os.path.expanduser("~/.local/bin/buzz")
    import time
    time.sleep(2)  # relay-lidmaatschap laten propageren vóór kanaal-adds
    # kanaal-id's uit channels.yml (bron), niet uit een geparste list
    chdef = yaml.safe_load(open(os.path.join(BOOMHUIS, "channels.yml"))).get("channels", {})
    for c in chans:
        cid = chdef.get(c, {}).get("id") or (GENERAL if c == "general" else None)
        if not cid:
            print(f"[create] kanaal '{c}' onbekend in channels.yml — sla lidmaatschap over")
            continue
        r = run([buzz, "channels", "add-member", "--channel", cid, "--pubkey", pub, "--role", "bot"], env=benv)
        print(f"[create] {c}-bot: {'ok' if 'accepted' in r.stdout and 'true' in r.stdout else r.stdout[:80] or r.stderr[:80]}")
    # eigen profielnaam
    run([buzz, "users", "set-profile", "--name", name, "--about", a.mandaat[:120]],
        env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))

    print(f"[create] {name} bedraad in boomhuis (identity/secrets/run-lijst/lidmaatschap/profiel).")
    print("VOLGENDE: (1) merge de handbook-PR (CODEOWNERS = Mark). "
          "(2) commit boomhuis (identities/secrets/agents.yml). "
          "(3) systemctl --user restart boomhuis-agents.service")


if __name__ == "__main__":
    main()
