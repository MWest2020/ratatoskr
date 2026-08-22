## Why

Zonder relay is er niets: geen kanalen, geen identiteiten, geen notificaties.
Fase 0 zet het fundament neer — een zelf-gehoste buzz-relay in closed mode, met
de eerste twee identiteiten (Mark als mens, de orchestrator als agent) — zodat
elke volgende fase alleen nog aansluit en niets meer hoeft te funderen.

## What Changes

- **`deploy/`**: een dunne wrapper om de upstream compose-bundle
  (`deploy/compose/` in block/buzz): onze `.env` (SOPS+age), gepinde
  `BUZZ_IMAGE`, Caddy/TLS-keuze, en een gedocumenteerde start/stop/backup.
  Geen fork, geen eigen compose tenzij upstream tekortschiet.
- **`identities.yml`**: de publieke registry — per identiteit de npub, de rol
  (`mens` | `orchestrator` | latere agentrollen), en de status
  (`actief` | `ingetrokken`).
- **`secrets/`**: SOPS+age-versleutelde privésleutels en relay-secrets
  (`BUZZ_RELAY_PRIVATE_KEY`, `BUZZ_GIT_HOOK_HMAC_SECRET`, db/S3-credentials).
- **`docs/how-to/relay-herstel.md`**: backup en restore, inclusief wat verloren
  mag gaan (berichten zijn spiegel) en wat nooit (relay-identiteit, sleutels).

## Capabilities

### New Capabilities

- `relay-deployment`: de zelf-gehoste relay — closed mode, gepind image,
  TLS, secrets-hygiëne en herstelbaarheid.
- `identity-registry`: één keypair per identiteit, publieke registry in git,
  privésleutels alleen via SOPS+age, intrekbaar.

### Modified Capabilities

<!-- Geen: dit is de eerste change van een greenfield-repo. -->

## Impact

- Nieuwe infra op één homelab-host (Postgres, Redis, MinIO, relay, Caddy);
  hostkeuze is een open beslissing van Mark (zie project.md).
- Nieuwe secret-klasse (Nostr-sleutels) onder het bestaande SOPS+age-regime.
- Habitat en handbook blijven onaangeroerd; er bestaat nog geen koppeling.
