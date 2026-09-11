# Change: technical-debt-11-09

## Why

De architect-review in #technical_debt (2026-09-11) vond drie plekken waar de
repo iets belooft dat hij niet doet. Elk is klein; samen zijn ze het patroon
waar `CLAUDE.md` voor waarschuwt: een regel die in proza bestaat en in de
praktijk afdrijft. Nagemeten op `main` (57492a5) en op de open PR #71
(`werk/sessietypes`), die op twee van de drie punten meebeweegt.

**1. Werksessies loggen odin, niet wie erom vroeg.** Schrijft odin een
`!sessie`-marker, dan geeft `agents/listener.py` alleen `odin` door; machtiging,
limiet, startpost en runbestand (`{typ}-odin-{ts}.jsonl`) kennen alleen odin.
Dat is een auditgat én een omweg: wie odin kan aanspreken, start via odin een
sessie op Marks vault, ook zonder zelf op `starters` te staan.

**2. "Immutable images" is geschreven, niet gehandhaafd.** Marks chat draait
via `scp` uit `/opt/buzz-build`, zonder image en zonder pin. De relay-compose
valt terug op `ghcr.io/block/buzz:main`; de echte pin staat alleen in de `.env`
op de host. De nieuwe `deploy/docker-compose.yml` uit PR #71 neemt die fallback
over, zet `CHAT_IMAGE` ook in `.env` en houdt drijvende tags.
`uitrol-voor-derden` laat Marks installatie buiten scope — juist de installatie
die elke dag draait blijft op het ongepinde pad.

**3. De 200-regelgrens is overschreden, zonder handhaving.** Op `main` vijf
bronbestanden (`test_topology.py` 241, `app.css` 230, `server.py` 221,
`buzzcli.py` 210, `auth.py` 203); PR #71 voegt er twee toe. Er is geen CI.
`chat/auth.py` bevat zelfgeschreven scrypt, TOTP en sessies en is niet door een
security-review gegaan: de vorige review (2026-08-30) dateert van vóór die code.

## What Changes

- **Een werksessie legt vast namens wie hij draait.** Naast de starter (wie de
  marker schreef) komt de `aanleiding`: de Nostr-afzender van het bericht dat de
  beurt in gang zette. Die staat in de naam van het runbestand, in een eerste
  regel daarin en in de startpost. Een sessie start alleen als starter én
  aanleiding op `starters` staan en de aanleiding `rol: mens` heeft in de
  registry. De limiet van één lopende sessie geldt per aanleiding.
  `orchestrator` hoort daardoor niet op `starters`.
- **Eén uitrolpad, en Marks installatie gaat er als eerste over** — vóór de
  eerste derde live gaat. De migratie uit PR #71 wordt uitgevoerd, niet alleen
  beschreven.
- **Pins staan letterlijk in het compose-bestand**, niet in `.env`, zonder
  fallback, minstens major.minor. `BUZZ_REF` in `chat/Dockerfile` volgt de
  relay-tag; workflows pinnen actions per SHA.
- **Een check in CI**: één workflow draait `verify.sh`, dat naast de unittests
  een regelgrens voor bronbestanden (met expliciete scope) en de pin-check
  draait. Bestaande overschrijdingen staan op een tijdelijke baseline die leeg
  moet zijn vóór archiveren.
- **Security-review van de auth-stack** (`auth.py`, `auth_store.py`,
  `auth_routes.py`, cookie- en proxy-afhandeling in `server.py`) als aparte
  sessie, met het verdict in `handover/`.

## Poort vóór de eerste derde

Geen installatie bij een derde, en het chat-package niet openbaar, zolang niet
alle drie gelden:

1. Marks chat draait uit het gepinde image in de compose-stack, zonder verlies
   van accounts of push-registraties.
2. De security-review heeft geen open High of Medium.
3. De check is groen in CI met een lege baseline.

## Wat hier NIET in zit

- **Een relay-sleutel per persoon in de webchat.** De webchat tekent alles met
  Marks sleutel, dus in een installatie met meer mensen is de aanleiding altijd
  `mark`. Dat is `identity-registry`-werk; deze change benoemt de grens.
- **Runbestanden duurzaam bewaren.** Ze staan in `/tmp/boomhuis-sessies` en
  overleven geen reboot. Eigen vraag.
- **SPDX-headers handhaven**, en `openspec/specs/webchat-pwa/spec.md` (288
  regels) opdelen. Markdown valt bewust buiten de regelgrens.

## Impact

- Specs: `werksessies` (twee eisen gewijzigd, één toegevoegd),
  `relay-deployment` (`Gepind image` gewijzigd, één eis toegevoegd), nieuw
  `repo-conventies`.
- Code bij apply: `agents/sessies.py`, `listener.py`, `prompts.py`,
  `bootstrap.py`, `sessies.yml` en tests; `deploy/docker-compose.yml`,
  `deploy/.env.example`, `.github/workflows/`; een check-script en `verify.sh`;
  splitsingen van de baseline-bestanden; `CLAUDE.md` en `openspec/project.md`.
- Andere changes: `uitrol-voor-derden` krijgt Marks installatie in scope en de
  image-tag gaat uit het env-bestand; die change wordt als eerste gearchiveerd.
- PR #71: deze PR voegt alleen bestanden onder deze change toe en botst niet;
  de taken gaan uit van wat #71 introduceert.
- Homelab-repo: na de migratie verdwijnen `ansible/files/boomhuis-chat.service`
  en de relay-compose-kopie, of worden een verwijzing naar `deploy/` hier.
- Draaiend: Marks chat ligt bij de migratie enkele minuten stil; terugvallen
  kan via de systemd-unit zolang die niet opgeruimd is.
