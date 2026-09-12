# Project: Ratatoskr (voorheen Boomhuis)

## Scope

De communicatielaag van Marks agent-ecosysteem: een zelf-gehoste buzz-relay
(Nostr) waarop mens en agents in kanalen samenwerken, plus de specs voor
identiteiten, kanaaltopologie, run-notificaties en een tweede klasse langlopende
chat-native agents. Ratatoskr weet níets van domeinlogica en voert zelf geen
repo-werk uit — dat blijft habitat.

Single-user platform voor Mark Westerweel. Persoonlijke infrastructuur.

## Waarom dit bestaat

Habitat bewees de gekooide executie, maar alle communicatie is vandaag
eenrichtingsverkeer door drie smalle media: env-vars in, git-branches uit, en
een tmux-pane als escalatiekanaal. Er is geen inbox, geen adressering buiten de
vaste rollenketen, geen notificatie als Mark niet aangekoppeld zit, en geen
bestaansplek voor rollen zonder code-deliverable. Buzz geeft precies de
ontbrekende laag — kanalen, threads, DM's, één identiteitsmodel voor mens en
agent met eigen sleutels en audit-spoor — als zelf-hostbaar open-source project
op een open protocol. Doel: één persoon die met een zwerm rollen bouwt,
reviewt, ontwerpt en vermarkt — asynchroon, herleidbaar, vanaf desktop en
telefoon.

## Handhaving (besloten 2026-09-12)

Conventies die niemand controleert, houden niet. Drie staan nu in `verify.sh`
én in CI (`.github/workflows/verify.yml`):

- **Regelgrens 200** — `scripts/line_limit.py`, met een baseline van wat bij
  invoering al te lang was. Die lijst mag alleen korter worden.
- **Pins** — `scripts/pin_check.py`: images letterlijk in het compose-bestand
  (niet in `.env`, dat staat op de host en niet in git), actions op commit-SHA,
  en `BUZZ_REF` gelijk aan de relay-tag.
- **Unittests** van `chat/`, `agents/` en `jobs/`.

Wat NIET in CI kan: de drie uitrol-lagen uit `chat/e2e/`. Die praten met een
echte relay achter een tailnet. Dat is een uitrol-stap, geen push-stap.

## Architectuur (besloten)

```
MENS (Mark: desktop/mobiel)        CHAT-NATIVE AGENTS (fase 2: buzz-acp,
        │                            eigen keypair, eigen host, geen push-creds)
        ▼                                    │
   ┌─────────────────────────────────────────▼───────┐
   │ buzz-relay — zelf-gehost, closed mode, TLS      │
   │ kanalen: #runs #escalatie #bouw #review         │
   │          #architectuur #marketing               │
   └─────────────────────────────────────────────────┘
        ▲ buzz-cli, post-only (fase 1)
        │
  orchestrator + dispatch.sh ──▶ habitat K8s Jobs (kooi, ONGEWIJZIGD)
        ▲                                    │
        └── git: branches, verdicts, audit-JSONL (de waarheid) ◀──┘
```

- **Relay**: upstream compose-bundle (relay, Postgres, Redis, MinIO) op een
  homelab-host via de homelab-blueprints, uitsluitend aan het tailnet,
  `RELAY_OWNER_PUBKEY` gezet (closed mode), image gepind.
- **Identiteiten**: één Nostr-keypair per identiteit; publieke registry
  (`identities.yml`) in deze repo; privésleutels SOPS+age.
- **Notificaties**: dispatch/orchestrator posten run-start, verdict en
  escalaties; best-effort — de relay kan een run nooit blokkeren.
- **Chat-native agents**: tweede agentklasse, langlopend via `buzz-acp`, alleen
  voor conversatie-deliverables; nooit in de habitat-namespace, nooit met
  git-push-credentials.

## Niet-doelen

- Geen federatie met publieke Nostr-relays; de relay blijft gesloten en privé.
- Buzz vervangt git niet als overdrachtsmedium van habitat; verdicts en audit
  blijven git-native.
- Geen relay-toegang vanuit de worker-kooi in fase 0–2; fase 3 vergt een
  expliciet amendement in habitat, proposal-first aldaar.
- Geen merge-automatisering; elke merge blijft bij Mark.
- Geen eigen chat-client of relay-forks; wij zijn afnemer van upstream.

## Conventies

- OpenSpec-flow: conversational design → propose → apply → archive. Geen code
  vóór "apply".
- Saai en auditeerbaar boven snel of slim; verworpen alternatieven in design.md.
- Python via `uv`, nooit `pip`. Bestanden ≤ 200 regels.
- Secrets alleen SOPS+age; nooit hardcoded, nooit gedecrypt gecommit.
- Immutable images, gepind per SHA/semver, nooit `:main`/`:latest`.
- Licentie: EUPL-1.2.

## Besloten (2026-08-22, door Mark)

1. **Bereik**: de relay hangt uitsluitend aan het Tailscale-net (tailnet); geen
   publieke voordeur. Of het ooit verder open moet is een latere, aparte
   beslissing. Mobiel bereik loopt via de Tailscale-app op de telefoon.
2. **Naam**: `boomhuis` (runner-up: `wolkenkrabber`) — een plek waar mensen, en
   dus ook agents, samenkomen.
3. **Host**: op homelab-infra, hergebruik van de terraform/ansible-blueprints
   uit de homelab-repo; de concrete host/VM-keuze is taak 1.1 van `add-relay`.
   Geen deploy op het habitat-K8s-cluster: de communicatielaag en de kooi delen
   bewust geen failure-domain (zie `add-relay/design.md`).

## Definition of done (v0 = fase 0 + 1)

De relay draait gepind en closed op een homelab-host, alleen via het tailnet
bereikbaar; Mark is aangemeld op desktop én telefoon (Tailscale-app); een echte
habitat-run post zijn start en
verdict (met link naar het HTML-run-rapport) in `#runs`; één escalatie landt in
`#escalatie` en bereikt Mark zonder dat hij aan tmux zit; de kooi-diff van
habitat is aantoonbaar leeg. Eén volledige loop, één keer.
