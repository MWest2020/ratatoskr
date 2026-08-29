# Change: rotate-mark-identity

> Besluit Mark 2026-08-28: "roteer de mark-nsec en fix de SOPS-hardening."

## Why

De nsec van identiteit `mark` is blootgesteld geweest: de oude chat-launcher
zette hem op de proces-commandline (ps-zichtbaar op vm 109, bekende
hardening-TODO in `chat/README.md`) en hij is op 2026-08-27 tijdens een
debug-sessie in een sessietranscript beland. Rotatie is de nette route; de
VM is tailnet/LAN-only dus de blootstelling was beperkt.

## Stand van de hardening (al gefixt vóór deze change)

De ps-blootstelling zelf is al gedicht: de chat draait inmiddels als
systemd-unit `boomhuis-chat.service` met `EnvironmentFile=
/opt/buzz-build/chat/chat.env` (root:600) — de sleutel staat niet meer in
argv. Deze change draait de sleutel zelf.

## What changes

- Nieuwe keypair voor `mark` (gegenereerd met `buzz-admin generate-key`):
  `pubkey_hex a05339f005904935da71e0498f3d542ac223e8cdfac920c6152a743f91640769`,
  `npub15pfnnuq9jpyntkn3upyc70259tpz86xdltyjp3s49f6rlytyqa5sn4zx8q`.
- Registry `identities.yml`: mark → nieuwe pubkey/npub + `geroteerd: 2026-08-28`.
- SOPS `secrets/identities.yaml`: mark `nsec`/`privkey_hex` → nieuwe waarden
  (geverifieerd via `--extract`-bytevergelijking).
- Relay-side (script `rotate-mark.sh`, door Mark uitgevoerd — de
  agent-permissielaag blokkeert membership-mutaties, terecht conform de
  invariant "een agent wijzigt nooit sleutels/relay-configuratie"):
  nieuwe pubkey is al relay-member; script doet kanaal-admin ×6 →
  `RELAY_OWNER_PUBKEY`-flip + relay-herstart → chat.env-flip + unit-herstart →
  verificatie (kanalen, chat-API, media-get) → oude pubkey uit de
  relay-membership + afwijzingscheck oude key.

## Verification

Nieuwe key: relay-member, kanaal-admin in alle zes kanalen, chat werkt,
media-get werkt. Oude key: geen relay-member meer, auth geweigerd.
