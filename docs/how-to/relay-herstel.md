---
status: actief
last_reviewed: 2026-08-25
---

# Relay-herstel (backup & restore)

Wat mag verloren gaan: berichthistorie (git is de waarheid). Wat nooit verloren
mag gaan: de **relay-identiteit** en de **secrets** — anders breekt elke client
en elke agent-config.

## Waar alles staat

| Wat | Waar | Backup |
|---|---|---|
| Relay-identiteit + HMAC | `/opt/buzz-relay/.env` op vm 109 | SOPS: `secrets/relay.yaml` (deze repo) |
| Identiteits-privésleutels | SOPS: `secrets/identities.yaml` | age-key: `~/.config/sops/age/keys.txt` op agent-lxc — **backup die key!** |
| Ledenlijst (owner/members) | Postgres in de stack | vzdump (hieronder); anders opnieuw via `buzz-admin add-member` |
| Berichthistorie | Postgres + MinIO volumes | best-effort via vzdump |
| Stack-definitie | homelab-repo `docker/buzz-relay/` + playbook | git |

## Backup

Proxmox `vzdump` van vm 109 (7 daily + 4 weekly, instellen in de Proxmox-UI,
conform het homelab-runbook). Dat dekt volumes, `.env` en ledenlijst ineens.

## Restore: schone host

1. VM opnieuw: `terraform apply` in `homelab/terraform/buzz-relay/` (of vzdump-restore).
2. Deploy: `ansible-playbook -i inventory/buzz-relay-hosts.yml playbooks/deploy-buzz-relay.yml`.
3. `.env` terugzetten: `sops -d secrets/relay.yaml` → waarden in `/opt/buzz-relay/.env`
   (plus nieuwe db/S3-wachtwoorden; die mogen vers). `RELAY_OWNER_PUBKEY` = mark
   uit `identities.yml`.
4. Playbook opnieuw draaien (pull + up).
5. Leden herstellen: `docker compose exec relay buzz-admin add-member --pubkey <hex> --role member`
   voor elke actieve identiteit in `identities.yml` (owner registreert zichzelf).
6. Smoke: vreemde sleutel geweigerd, bericht mark↔orchestrator beide richtingen.

Geoefend: 2026-08-25 (herstart-variant: relay-container herstart zonder
identiteitsverlies, clients hoefden niets opnieuw; volledige schone-host-restore
nog niet geoefend).

## Bekende valkuil

MinIO eist x86-64-v2: de VM moet `cpu: host` hebben (staat in terraform;
CHANGELOG homelab 2026-08-22). Zonder dat crasht de stack op "Fatal glibc error".
