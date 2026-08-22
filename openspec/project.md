# Project: Korf

## Scope

De communicatielaag van Marks agent-ecosysteem: een zelf-gehoste buzz-relay
(Nostr) waarop mens en agents in kanalen samenwerken, plus de specs voor
identiteiten, kanaaltopologie, run-notificaties en een tweede klasse langlopende
chat-native agents. Korf weet níets van domeinlogica en voert zelf geen
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

- **Relay**: upstream compose-bundle (relay, Postgres, Redis, MinIO, Caddy/TLS)
  op een homelab-host, `RELAY_OWNER_PUBKEY` gezet (closed mode), image gepind.
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

## Open beslissingen (voor Mark, niet gokken)

1. **Host**: welke homelab-VM/LXC draagt de compose-stack (Postgres+Redis+MinIO
   erbij)? Korf kiest geen host en tast geen infra af zonder Marks aanwijzing.
2. **Mobiel bereik**: relay alleen op het interne net/VPN, of publiek achter
   Caddy met TLS? Bepaalt of de push-gateway (fase 1+) nodig is.
3. **Naam**: `korf` is het voorstel (bijenkorf, past bij buzz); alternatieven
   `zwerm`, `raat`.

## Definition of done (v0 = fase 0 + 1)

De relay draait gepind en closed op een homelab-host met TLS; Mark is
aangemeld op desktop én telefoon; een echte habitat-run post zijn start en
verdict (met link naar het HTML-run-rapport) in `#runs`; één escalatie landt in
`#escalatie` en bereikt Mark zonder dat hij aan tmux zit; de kooi-diff van
habitat is aantoonbaar leeg. Eén volledige loop, één keer.
