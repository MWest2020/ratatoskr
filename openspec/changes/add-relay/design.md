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

## Compose, niet Kubernetes

De relay draait via de upstream compose-bundle op een VM/LXC, níet op het
K8s-cluster van habitat. Redenen: (a) de kooi en de communicatielaag delen dan
geen failure-domain en geen namespace; (b) upstream onderhoudt de compose-route
als eersteklas pad inclusief TLS; (c) saai en herstelbaar wint van "alles op
k8s". Een latere verhuizing blijft mogelijk (het is Postgres+Redis+MinIO+één
container). Buzz' eigen `buzz-backend-kubernetes` komt pas in beeld bij fase 2+
en dan alleen voor agents, niet voor de relay.

## Wat mag verloren gaan

Berichten zijn coördinatie, geen waarheid. Backup-doel: de relay-identiteit en
sleutels overleven altijd (anders breekt elke client en elke agent-config);
berichthistorie is best-effort (Postgres-dump). Een restore die historie mist is
een geldige restore.
