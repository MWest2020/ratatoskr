# Design: add-relay

## Keuze: buzz — en de verworpen alternatieven

| Optie | Waarom verworpen |
|---|---|
| Slack/Discord | Niet zelf-gehost; agents zijn er tweederangs bots met permission-flags in plaats van volwaardige identiteiten; data buiten eigen beheer. |
| Matrix (Synapse/Dendrite) | Wél zelf-gehost en volwassen, maar alle agent-integratie (CLI met JSON-I/O, agent-harnas, git-events) zou eigen bouwwerk zijn. |
| Zulip | Goede threads, zelf-hostbaar, maar zelfde bezwaar: agent-first laag ontbreekt, identiteitsmodel is accounts+bots. |
| Niets (GitHub issues/PR's als kanaal) | Geen realtime, geen mobiele escalatie, geen DM's, en geen plek voor rollen zonder repo-deliverable. |

Buzz geeft out-of-the-box wat wij anders bouwen: één identiteitsmodel voor mens
en agent (eigen keypair + audit-spoor), `buzz-cli` (JSON in/uit, gemaakt voor
LLM-toolcalls), `buzz-acp` (harnas met o.a. Claude Code-ondersteuning), en
kanalen/threads/DM's op een open protocol (Nostr) met de data in onze eigen
Postgres. Backing: Block, Apache-2.0, ~30k stars, actieve ontwikkeling.

## Risico: buzz is jong

Workflow-triggers en git-hosting zijn upstream nog in aanbouw. Mitigatie:

1. Wij gebruiken in fase 0–1 alleen het stabiele deel (relay, kanalen, threads,
   DM, media, search, buzz-cli).
2. `BUZZ_IMAGE` gepind per SHA/semver; upgrades zijn bewuste, gelogde
   pin-wijzigingen in git.
3. Exit-strategie: Nostr is een open protocol en de events staan in onze eigen
   Postgres — migreren naar een andere relay-implementatie blijft mogelijk, en
   omdat git de waarheid blijft is zelfs totaalverlies van de relay geen verlies
   van gezaghebbende state.

## Closed mode vanaf dag één

`RELAY_OWNER_PUBKEY` gezet: alleen identiteiten uit de registry komen binnen.
Een open relay op het thuisnetwerk is een aanvalsoppervlak zonder enige
opbrengst voor een single-user platform.

## Tailnet-only (besloten door Mark)

De relay hangt uitsluitend aan het Tailscale-net: geen poort naar het publieke
internet, geen publieke DNS. Gevolgen: (a) transport is al versleuteld
(WireGuard), dus Caddy/Let's Encrypt is geen vereiste — hooguit een
`tailscale serve`/cert als een client per se `wss://` met geldig certificaat
wil, uit te zoeken bij apply; (b) mobiel bereik loopt via de Tailscale-app,
zodat escalaties de telefoon halen zonder iets open te zetten; (c) verdediging
in twee lagen: het tailnet bepaalt wie de relay überhaupt kan bereiken, closed
mode bepaalt wie er mag spreken. Verder openzetten is een latere, aparte
change.

## Compose, niet Kubernetes

De relay draait via de upstream compose-bundle op een VM/LXC, níet op het
K8s-cluster van habitat. Het kán technisch prima op k8s — het is
Postgres+Redis+MinIO+één container — maar bewust niet: (a) de kooi en de
communicatielaag delen dan geen failure-domain en geen namespace (valt het
cluster, dan wil je juist kunnen praten over waarom); (b) upstream onderhoudt
de compose-route als eersteklas pad; (c) saai en herstelbaar wint van "alles op
k8s". Provisioning en configuratie hergebruiken de terraform/ansible-blueprints
uit de homelab-repo. Een latere verhuizing naar k8s blijft mogelijk. Buzz' eigen `buzz-backend-kubernetes` komt pas in beeld bij fase 2+
en dan alleen voor agents, niet voor de relay.

## Deploy volgt het homelab-patroon (besloten na blueprint-verkenning)

De homelab-repo heeft een bewezen vijflagenpatroon voor precies dit:
`terraform/<stack>/` (kopie van `nginx-lab`, dé referentie) → `/32`-route in
`inventory/group_vars/hypervisors.yml` → `inventory/<stack>-hosts.yml` →
`docker/<stack>/` → `playbooks/deploy-<stack>.yml` (Docker-install + `/opt/<stack>`
+ `.env`-seeding zit al in `deploy-openwoo-acc.yml` om te kopiëren). Daarom
leven de **deploy-artefacten in de homelab-repo** (stacknaam `buzz-relay`,
vm 109, 192.168.178.60 — eerstvolgende vrije slots) en houdt boomhuis de spec,
de kanaal-/identiteitsregistry en de buzz-eigen configuratie. Eén
deploy-conventie per platform; geen tweede optuigen.

Consequenties uit de verkenning:

- **Template 9001 eerst.** Het standaard-template (9000) is 2c/2GB/20GB; de
  stack (Postgres+Redis+MinIO+relay) wil ~4GB+/30GB+. Hardware-overrides in
  terraform zijn in de homelab-repo verboden (bpg-provider hangt op qmset);
  de sanctionele route is een groter template bouwen per
  `docs/how-to/07-vm-provisioning-stack.md`.
- **Tailnet-bereik via een `/32`-subnetroute** op de proxmox-laptop, zoals alle
  .50-.59-VM's — géén Tailscale in de VM als eerste stap. Poorten binden op het
  LAN-IP, UFW deny-in conform `configure-firewall.yml`. Terugvaloptie als
  clients per se `wss://` met geldig certificaat willen: de repo-lokale
  tailscale-role (`claude-lxc-iac/ansible/roles/tailscale/`) in de VM +
  MagicDNS-naam; dat is een taak-beslissing, geen spec-wijziging.
- **Secrets in twee regimes, elk native.** Infra-secrets (Postgres/MinIO/relay-
  env) volgen het homelab-patroon: `env.example` in git, echte `.env` 0600 op
  de host, desnoods on-host gegenereerd (`openssl rand`) — de homelab-repo
  gebruikt geen SOPS. Identiteits-privésleutels (Nostr) zijn boomhuis-domein en
  blijven SOPS+age in deze repo, zoals habitat dat al doet.
- **K8s was een reëel alternatief** (het cluster heeft al CNPG-Postgres, MinIO
  en de Tailscale-operator), maar de vertaling compose→manifests is het dure
  deel en het failure-domain-argument blijft staan. Bewust VM.

## Wat mag verloren gaan

Berichten zijn coördinatie, geen waarheid. Backup-doel: de relay-identiteit en
sleutels overleven altijd (anders breekt elke client en elke agent-config);
berichthistorie is best-effort (Postgres-dump). Een restore die historie mist is
een geldige restore.
