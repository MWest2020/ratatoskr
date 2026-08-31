# Tasks: add-relay

> Deploy-artefacten landen in de homelab-repo (eigen werkwijze dáár, incl.
> CHANGELOG-entry en `terraform fmt`); boomhuis houdt spec, registry en
> identiteitssleutels. Hostplan: stack `buzz-relay`, vm 109, 192.168.178.60.

Benodigd van Mark (blokkerend, alleen hij kan dit leveren):

- [x] 0.1 Proxmox API-token (`TF_VAR_proxmox_api_token`, staat in `~/homelab/.env`
      op jumpy) of Mark draait de `terraform apply` zelf
- [x] 0.2 Bevestiging vm-id/IP (109/.60) en go voor `terraform apply`
      (homelab-CLAUDE.md eist expliciete bevestiging)
- [x] 0.3 Eénmalige route-goedkeuring `192.168.178.60/32` in de
      Tailscale-adminconsole

Uitvoering:

- [x] 1.1 Template 9002 bouwen (9001 bleek bezet: k8s-cp-template) (groter dan 9000: ≥2c/4GB/30GB) per
      `docs/how-to/07-vm-provisioning-stack.md` in de homelab-repo
- [x] 1.2 `terraform/buzz-relay/` (kopie nginx-lab-stijl, clone van 9002 + cpu:host,
      vm 109, .60); `terraform fmt`; plan → apply na 0.2
- [x] 1.3 `/32`-route toevoegen aan `group_vars/hypervisors.yml` +
      `configure-tailscale-routes.yml` draaien; goedkeuren (0.3)
- [x] 1.4 `docker/buzz-relay/` op basis van upstream `deploy/compose/`:
      `BUZZ_IMAGE` gepind op concrete SHA/semver, poorten alleen op het LAN-IP,
      geen Caddy; `env.example` zonder echte waarden
- [x] 1.5 `playbooks/deploy-buzz-relay.yml` (kopie deploy-openwoo-acc.yml
      zonder certbot/cloudflare) + `inventory/buzz-relay-hosts.yml`; UFW
      deny-in, alleen 22 + relay-poort vanaf beheer/tailnet-route
- [x] 1.6 `.env` op de host vullen (relay-sleutel, HMAC, db/S3); relay starten
      in closed mode (`RELAY_OWNER_PUBKEY`)
- [x] 1.7 `identities.yml` in boomhuis: keypairs voor Mark (mens) en
      orchestrator (agent); npubs in de registry, privésleutels SOPS+age in
      `secrets/`
- [ ] 1.8 Clients aanmelden — mobiel BEWEZEN (relay bereikbaar via tailnet op de telefoon, 2026-08-26); desktop-client en buzz-cli voor de orchestrator nog open (telefoon via de
      Tailscale-app); `buzz-cli` werkend als orchestrator-identiteit vanaf de
      orchestrator-host; als clients `wss://` afdwingen: tailscale-role in de
      VM + MagicDNS als terugvaloptie (zie design.md)
- [x] 1.9 Live smoke vóór afronding: bericht Mark↔orchestrator in beide
      richtingen; vreemde pubkey geweigerd; van buiten het tailnet geen
      verbinding; relay-herstart zonder identiteitsverlies
- [x] 1.10 `docs/how-to/relay-herstel.md`: backup (Proxmox vzdump conform
      homelab-runbook + Postgres-dump) en restore beschreven en één keer
      geoefend
