#!/usr/bin/env bash
# Maak één Nostr-sleutelpaar voor een boomhuis-installatie.
#
# Waarom dit bestand bestaat: een verse installatie heeft minstens twee sleutels
# nodig (RELAY_OWNER_PUBKEY en BUZZ_PRIVATE_KEY), en de buzz-CLI kan ze niet maken.
# Zonder dit script zou "genereer een keypair" een stap zijn die in geen enkel
# bestand staat — en dan is de installatie geen installatie maar een reconstructie.
#
# Gebruikt alleen docker, dat je toch al hebt. Twee stappen met opzet: de
# afhankelijkheden worden MET netwerk geïnstalleerd, de sleutel wordt ZONDER
# netwerk gemaakt (`--network none`). Er wordt niets bewaard; wat je op het scherm
# ziet is het enige exemplaar.
#
#   bash sleutelpaar.sh
#
# De privésleutel hoort in .env (mode 0600) en nergens anders — niet in git, niet
# in een chatbericht, niet in je shell-geschiedenis.
set -euo pipefail

img=$(docker build -q - <<'DOCKERFILE'
FROM python:3.12-slim
RUN pip install --no-cache-dir --quiet coincurve bech32
COPY <<'PY' /sleutelpaar.py
from coincurve import PrivateKey
from bech32 import bech32_encode, convertbits

k = PrivateKey()
priv = k.secret.hex()
pub = k.public_key.format(compressed=True)[1:].hex()   # x-only, zoals Nostr wil


def b32(prefix, hexdata):
    return bech32_encode(prefix, convertbits(bytes.fromhex(hexdata), 8, 5))


print("privesleutel (nsec) :", b32("nsec", priv))
print("privesleutel (hex)  :", priv)
print("pubkey (npub)       :", b32("npub", pub))
print("pubkey (hex)        :", pub)
PY
DOCKERFILE
)

docker run --rm --network none "$img" python /sleutelpaar.py

cat <<'TXT'

Waar dit heen gaat:
  pubkey (hex)         -> RELAY_OWNER_PUBKEY   (de eigenaar van de relay)
  privesleutel (nsec)  -> BUZZ_PRIVATE_KEY     (waarmee de chat post)

Voor een installatie met één persoon mag dat hetzelfde paar zijn. Wil je de
beheerder en de chat scheiden, draai dit script dan twee keer en maak het tweede
paar lid van de relay.
TXT
