#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# /// script
# dependencies = ["coincurve", "bech32", "pyyaml"]
# ///
"""Geef een verse installatie zijn eigen identiteiten.

Zonder dit is "installeer ratatoskr" voor een derde geen installatie maar een
overname: hij zou Marks sleutels moeten gebruiken, en dan draaien twee
installaties op dezelfde npub. Voor een Nostr-relay is dat niet "twee
installaties" maar één identiteit die zich tegenspreekt.

Idempotent, en dat is hier geen nettigheid maar een eis: een tweede run mag
nooit een bestaande sleutel vervangen. Doet hij dat wel, dan is elke agent die
met de oude sleutel gepost heeft zijn geschiedenis kwijt en moet elk kanaal
opnieuw lidmaatschap krijgen.

    uv run scripts/init_identities.py --map ~/.config/ratatoskr/keys
    uv run scripts/init_identities.py --map … --registry identities.yml --dry-run

De privésleutel verschijnt niet op het scherm. Wat je ziet is de npub, en dat is
het deel dat je mag delen — zie `deploy/sleutelpaar.sh`, dat dezelfde curve en
dezelfde bech32-codering gebruikt maar één sleutel tegelijk en via docker.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents"))

import keystore  # noqa: E402


def sleutelpaar():
    """(nsec, npub) — secp256k1 plus bech32, zoals Nostr het wil.

    Dezelfde berekening als `deploy/sleutelpaar.sh`, hier in Python zodat een
    installatie geen docker nodig heeft om één sleutel te maken.
    """
    from bech32 import bech32_encode, convertbits
    from coincurve import PrivateKey

    sk = PrivateKey()
    # x-only pubkey: Nostr gebruikt de 32 bytes ná het prefix-byte.
    pub = sk.public_key.format(compressed=True)[1:]
    nsec = bech32_encode("nsec", convertbits(sk.secret, 8, 5))
    npub = bech32_encode("npub", convertbits(pub, 8, 5))
    return nsec, npub


def lees_registry(pad):
    import yaml
    if not os.path.exists(pad):
        return {"identities": {}}
    with open(pad) as f:
        return yaml.safe_load(f) or {"identities": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="sleutelopslag (mode 0700)")
    ap.add_argument("--registry", default="identities.yml", help="publieke registry")
    ap.add_argument("--handles", default="", help="komma-gescheiden; leeg = uit de registry")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    reg = lees_registry(a.registry)
    identiteiten = reg.get("identities") or {}
    handles = ([h.strip() for h in a.handles.split(",") if h.strip()]
               or sorted(identiteiten))
    if not handles:
        print(f"[init] geen handles: geef --handles of vul {a.registry}", file=sys.stderr)
        return 1

    nieuw, bestond = [], []
    for h in handles:
        pad = os.path.join(a.map, f"{h}.nsec")
        if os.path.exists(pad):
            bestond.append(h)
            continue
        if a.dry_run:
            nieuw.append((h, "(dry-run)"))
            continue
        nsec, npub = sleutelpaar()
        keystore.schrijf_bestand(a.map, h, nsec)
        identiteiten.setdefault(h, {})["npub"] = npub
        nieuw.append((h, npub))

    for h, npub in nieuw:
        print(f"[init] nieuw: {h}  {npub}")
    if bestond:
        print(f"[init] bestond al, ongemoeid gelaten: {', '.join(bestond)}")

    if nieuw and not a.dry_run:
        import yaml
        reg["identities"] = identiteiten
        tmp = a.registry + ".tmp"
        with open(tmp, "w") as f:
            yaml.safe_dump(reg, f, allow_unicode=True, sort_keys=True)
        os.replace(tmp, a.registry)
        print(f"[init] publieke helften in {a.registry}")
    print(f"[init] klaar: {len(nieuw)} nieuw, {len(bestond)} bestond al. "
          f"Privésleutels staan in {a.map} en nergens anders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
