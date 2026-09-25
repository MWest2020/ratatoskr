# Change: het oude uitrolpad opruimen

## Why

Marks installatie draait sinds 2026-09-11 als compose-stack uit een gepind image
(inmiddels 0.7.0). Het oude pad staat er nog: de systemd-unit
`boomhuis-chat.service` in de homelab-repo, de checkout in `/opt/buzz-build/chat`,
en de oude relay-map `docker/buzz-relay/`. Dat is met opzet zo gelaten — het oude
volume en de oude unit zijn de weg terug.

Nu is het dood gewicht dat een verkeerde indruk wekt: wie op die VM kijkt ziet
twee manieren om de chat te draaien en weet niet welke de echte is.

Deze change is **tijd-gebonden**: hij gaat pas open als de compose-kant een week
zonder terugval draait. Hij is uit `technical-debt-11-09` gesplitst omdat een
change openhouden om een kalender af te wachten de takenlijst onbetrouwbaar
maakt — dan staat er iets open dat op niemand wacht.

## What Changes

- Homelab-PR: `ansible/files/boomhuis-chat.service` weg, en `docker/buzz-relay/`
  vervangen door een verwijzing naar `deploy/` in deze repo (het playbook dat
  `.env` zaait gaat mee).
- `/opt/buzz-build/chat` opruimen op de VM, inclusief het oude volume
  `buzz-prod_boomhuis-chat-data` — pas als de nieuwe kant bewezen staat.
- `chat/README.md` en `docs/how-to/inloggen.md` noemen `/opt/buzz-build` niet
  meer.

## Impact

- Raakt de homelab-repo, de relay-VM en twee documenten hier.
- **Voorwaarde:** een week zonder terugval, en `chat/e2e/after-deploy.sh` groen
  op de dag van opruimen. Zonder dat blijft het oude pad staan; het kost niets
  behalve verwarring, en die is goedkoper dan een verdwenen weg terug.
