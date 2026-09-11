# Werken in de Ratatoskr-repo

Dit is het conventie-bestand voor wie in *deze* repo (`MWest2020/ratatoskr`) werkt.
Mandaten voor chat-native agents zijn iets anders en landen per agent onder
`agents/` (change `add-chat-native-agents`).

## Wat Ratatoskr is

De communicatielaag van het ecosysteem (Yggdrasil): een zelf-gehoste buzz-relay plus de
specs voor kanalen, identiteiten, notificaties en chat-native agents. Ratatoskr voert
zelf niets uit — executie is habitat, kennis is handbook.

## Werkwijze

- **OpenSpec-flow**: conversational design → `propose` → `apply` → `archive`.
  Geen code of deployment vóór een change op "apply" staat.
- **Saai en auditeerbaar boven snel of slim.** Elke niet-voor-de-hand-liggende
  keuze staat in een `design.md` mét verworpen alternatieven.

## Harde invarianten (niet-onderhandelbaar)

- **Git is de waarheid.** Buzz spiegelt; het vervangt nooit branches, verdicts
  of audit-JSONL als gezaghebbende bron.
- **De kooi blijft dicht.** Geen relay-egress, geen buzz-sleutels en geen
  `.mcp.json` voor habitat-workers zonder een expliciet, door Mark goedgekeurd
  amendement op habitats `worker-execution`-spec.
- **Geen secret leesbaar in git.** Nostr-privésleutels van identiteiten: alleen
  SOPS+age-versleuteld in deze repo. Infra-secrets (relay, HMAC, db/S3): alleen
  als `.env` op de host, conform het homelab-patroon. Publieke sleutels horen
  in `identities.yml`.
- Een agent wijzigt nooit zijn eigen mandaat, sleutels of de relay-configuratie.

## Conventies

- **Code is Engels, proza is Nederlands** — inclusief de commentaren, want die
  leggen uit *waarom* iets zo is. Zie [ADR-0001](docs/adr/0001-code-in-het-engels.md)
  voor wat er precies onder "code" valt en wat niet. Bestaande Nederlandse
  identifiers worden in één aparte change omgezet, niet gaandeweg.
- Python via `uv`, nooit `pip`. Bestanden ≤ 200 regels. Bare scripts, geen
  ceremonie.
- Immutable images: `BUZZ_IMAGE` gepind per SHA of semver-tag, nooit `:main` of
  `:latest`.
- Licentie: EUPL-1.2. Nieuwe bronbestanden krijgen een SPDX-header.
