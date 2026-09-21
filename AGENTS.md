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

## De kern: niet aanpassen zonder borging

Mark, 2026-09-13: *"de kern moet geborgd worden. unit test, integration tests,
niet aanpassen zonder borging."*

Er zijn vier ketens waar een storing **stil** is — je ziet geen fout, je ziet
niets, en dat is niet te onderscheiden van "er is geen nieuws". Die krijgen geen
regel code erbij zonder een test die de verandering vastpint:

| keten | unit | integratie |
|---|---|---|
| Web Push | `chat/test_push.py`, `orchestrator/test_push_subs_helper.py` | `orchestrator/test_push_chain.py`, `orchestrator/test_push_send.py`, `chat/e2e/push-states.js` |
| Inloggen en sessies | `chat/test_auth*.py` | `chat/e2e/login-flow.js` |
| De relay-verbinding | — | `chat/e2e/connection.sh` |
| De app-schil | `chat/test_server.py` | `chat/e2e/smoke.js` |

Twee regels die daaruit volgen:

- **Een unittest per bestand bewijst de keten niet.** Alle drie de push-storingen
  van 11–13 september zaten in de *overgang* tussen twee onderdelen die elk hun
  eigen groene tests hadden. Raak je een naad aan — een pad, een eigenaar, een
  formaat dat twee kanten moeten delen — dan hoort daar een test bij die beide
  kanten aanroept.
- **Stil falen is de fout, niet alleen de storing.** Een `catch` die de reden
  weggooit, een lege lijst waar een leesfout hoorde te staan, een knop die buiten
  beeld valt: dat zijn geen cosmetische punten, dat is de reden dat een storing
  dagen duurt. Een nieuwe faalweg moet zeggen wát er mis is.

Wat een e2e-test nodig heeft (Playwright, een testaccount, de VM) staat in
`chat/e2e/README.md`. Draait een laag niet, dan is de uitrol niet groen —
overslaan telt niet als slagen.

## Conventies

- **Engels in de repo, Nederlands in het gesprek.** Alles wat blijft staan —
  code, commentaar, docs, commit-teksten, interfaceteksten — is Engels; wat we
  tegen elkaar zeggen is Nederlands. Zie
  [ADR-0001](docs/explanation/adr/0001-code-in-het-engels.md). Nieuw werk meteen Engels; het
  bestaande Nederlands gaat in één aparte change om, niet gaandeweg.
- Python via `uv`, nooit `pip`. Bare scripts, geen ceremonie.
- **Bestanden ≤ 200 regels**, gehandhaafd door `scripts/line_limit.py` (in
  `verify.sh` en in CI). Scope: `.py .js .sh .css .html` en `Dockerfile`.
  Markdown, YAML en JSON tellen niet mee — dat is proza of data, en "splits je
  config op" is geen verbetering. Uitzonderingen staan mét reden in dat script.
  Wat bij invoering al te lang was staat op een baseline die alleen korter mag
  worden.
- **Immutable images: de pin staat letterlijk in `deploy/docker-compose.yml`**,
  niet in `.env` — een pin op de host staat niet in git, en dan lopen "wat
  draait er" en "wat zegt de repo" uiteen. Geen variabele, geen `:-fallback`,
  minstens major.minor. GitHub-actions op commit-SHA. `scripts/pin_check.py`
  bewaakt alle drie. Lokale guard: `bash scripts/install_hooks.sh` draait
  `verify.sh` vóór een push naar `main`. **Dat is de poort, en dat blijft het.**
  Niet voorstellen om dit bij GitHub af te dwingen — Mark wil dat niet, en dat is
  vier keer gezegd.
- Licentie: MIT. Nieuwe bronbestanden krijgen een SPDX-header.
