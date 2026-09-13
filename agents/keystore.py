#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Waar een privésleutel vandaan komt — een keuze van de installatie.

Vandaag staat dat vast in de repo: `agents/run.sh` doet `sops -d
secrets/identities.yaml` met Marks age-sleutel. Dat werkt voor Marks installatie
en voor niemand anders: een derde heeft dat bestand niet en die sleutel niet, en
kan dus geen enkele agent starten.

Erger is de stille aanname eronder. Zou een derde de repo mét `secrets/`
overnemen, dan draaien twee installaties op dezelfde npub — en voor een
Nostr-relay is dat niet "twee installaties", dat is één identiteit die zich
tegenspreekt. "Eén installatie = één team" (besluit C in
docs/naar-een-product.md) is op sleutelniveau pas waar als de sleutels bij de
installatie ontstaan.

Twee backends, meer niet:

- **`sops`** — wat Marks installatie doet. Die blijft werken; een terugweg gooi
  je niet weg in de change die de nieuwe weg aanlegt.
- **`bestand`** — een map op de installatie, één bestand per handle, mode 0600.

Fail-closed op twee manieren, en de tweede is de interessante: een ontbrekende
sleutel levert geen sleutel op, en een sleutel die te ruim leesbaar is óók niet.
Een sleutelbestand met mode 0644 is geen sleutelopslag maar een publicatie, en
die stilzwijgend accepteren is precies het soort "het werkt toch" dat later een
incident heet.
"""
import os
import re
import stat
import subprocess

NSEC = re.compile(r"^nsec1[02-9ac-hj-np-z]{58}$")


class SleutelFout(Exception):
    """Kon niet aan een sleutel komen, mét de reden. Nooit stil."""


def _lees_sops(pad, handle):
    if not os.path.exists(pad):
        raise SleutelFout(f"{pad} bestaat niet")
    p = subprocess.run(["sops", "-d", pad], capture_output=True, text=True)
    if p.returncode != 0:
        raise SleutelFout(f"sops-decrypt faalde: {(p.stderr or p.stdout).strip()[:120]}")
    # Bewust geen yaml-parse: de structuur is `  <handle>:\n    nsec: ...` en de
    # bestaande run.sh leest hem met awk op precies die vorm. Eén parser erbij
    # zou een tweede waarheid over hetzelfde bestand zijn.
    zoek, gevonden = f"  {handle}:", False
    for regel in p.stdout.splitlines():
        if regel.rstrip() == zoek:
            gevonden = True
            continue
        if gevonden:
            if regel.strip().startswith("nsec:"):
                return regel.split(":", 1)[1].strip()
            if regel and not regel.startswith("    "):
                break
    raise SleutelFout(f"geen nsec voor '{handle}' in {pad}")


def _lees_bestand(map_, handle):
    pad = os.path.join(map_, f"{handle}.nsec")
    if not os.path.exists(pad):
        raise SleutelFout(f"{pad} bestaat niet")
    modus = stat.S_IMODE(os.stat(pad).st_mode)
    if modus & 0o077:
        raise SleutelFout(
            f"{pad} heeft modus {modus:04o} — te ruim leesbaar, verwacht 0600. "
            "Een sleutel die anderen kunnen lezen is geen sleutel.")
    with open(pad) as f:
        return f.read().strip()


def lees(handle, backend=None, sops_pad=None, map_=None):
    """De privésleutel van `handle`, of `SleutelFout` met de reden.

    `backend` uit `RATATOSKR_KEYSTORE` (default `sops`), zodat een installatie
    het omzet zonder de code te raken.
    """
    backend = (backend or os.environ.get("RATATOSKR_KEYSTORE") or "sops").lower()
    if backend == "sops":
        sleutel = _lees_sops(sops_pad or os.environ.get(
            "RATATOSKR_SOPS_IDENTITIES", "secrets/identities.yaml"), handle)
    elif backend == "bestand":
        sleutel = _lees_bestand(map_ or os.environ.get(
            "RATATOSKR_KEYDIR", os.path.expanduser("~/.config/ratatoskr/keys")), handle)
    else:
        raise SleutelFout(f"onbekende backend '{backend}' (kies: sops, bestand)")
    if not NSEC.match(sleutel):
        # Vorm controleren vóór gebruik: een half gelezen bestand of een
        # yaml-anker levert anders een "sleutel" op waarmee de relay je
        # weigert, en dan zoek je het bij de relay.
        raise SleutelFout(f"'{handle}': geen geldige nsec (kreeg {len(sleutel)} tekens)")
    return sleutel


def schrijf_bestand(map_, handle, nsec):
    """Leg een sleutel neer zoals een sleutel hoort te liggen: 0700/0600."""
    if not NSEC.match(nsec):
        raise SleutelFout(f"'{handle}': geen geldige nsec, niet weggeschreven")
    os.makedirs(map_, mode=0o700, exist_ok=True)
    os.chmod(map_, 0o700)
    pad = os.path.join(map_, f"{handle}.nsec")
    # O_EXCL: nooit een bestaande sleutel overschrijven. Dat is geen
    # voorzichtigheid maar het verschil tussen idempotent en destructief —
    # overschrijven maakt elke agent die die sleutel gebruikte onbereikbaar.
    fd = os.open(pad, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(nsec + "\n")
    return pad
