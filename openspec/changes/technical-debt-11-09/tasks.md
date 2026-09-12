# Tasks — technical-debt-11-09

## 0. Afstemmen met lopend werk

- [x] 0.1 Stand van PR #71 vastleggen: deze taken gaan uit van de bestanden die
      #71 introduceert (`deploy/`, `chat/Dockerfile`, `chat-image.yml`, de
      extra sessietypes). Landt #71 later, dan deze taken daarop bijstellen.
- [x] 0.2 `uitrol-voor-derden` bijwerken: Marks installatie uit "Wat hier NIET
      in zit" naar de scope; taak 6.1 wordt "uitvoeren"; het scenario "Een
      upgrade is een diff" noemt het compose-bestand, niet het env-bestand.

## 1. Werksessies: aanleiding

- [x] 1.1 `bootstrap.py`: `rol` per identiteit uit `identities.yml` beschikbaar
      voor de listener.
- [x] 1.2 `sessies.mag_starten`: starter én aanleiding op `starters`, aanleiding
      `rol: mens`, limiet per aanleiding. Een weigering noemt welke voorwaarde
      faalde.
- [x] 1.3 `Register.start`: runbestand `{typ}-{aanleiding}-{ts}.jsonl`, met als
      eerste regel starter, aanleiding, bericht-id en kanaal.
- [x] 1.4 `listener.py`: bij een agent-antwoord schrijver en id van het
      aansturende bericht doorgeven; startpost en logregel "gestart door
      @starter namens @aanleiding".
- [x] 1.5 `prompts.sessie_clausule`: alleen types die voor deze aanleiding
      startbaar zijn.
- [x] 1.6 `sessies.yml`: `orchestrator` blijft op `starters` (besluit Mark
      2026-09-11) — geen wijziging, wel vastleggen in de how-to waaróm, en wat
      het kost voor de herleiding.
- [x] 1.7 Tests: agent namens niet-starter geweigerd; aanleiding `orchestrator`
      toegestaan (staat op `starters`); twee mensen via odin tegelijk toegestaan;
      tweede sessie van dezelfde persoon via odin geweigerd; meta-regel wordt
      door de oogst overgeslagen; bestandsnaam.
- [x] 1.8 `docs/how-to/werksessies.md`: aanleiding, limiet per persoon, en de
      grens dat webchat-berichten als `mark` tekenen.
- [ ] 1.9 Live: odin start op Marks verzoek een sessie; runbestand en startpost
      noemen `mark` als aanleiding.

## 2. Eén uitrolpad, pin in git

- [x] 2.1 `deploy/docker-compose.yml`: elk `image:` letterlijk, zonder
      variabele; drijvende tags naar minstens major.minor.
- [x] 2.2 `CHAT_IMAGE` en `BUZZ_IMAGE` uit `deploy/.env.example`;
      `docs/how-to/installeren.md`: een upgrade is een nieuwe compose-versie.
- [x] 2.3 `.github/workflows/chat-image.yml`: actions per commit-SHA.
- [x] 2.4 Pin-check (onderdeel van 3.1): `image:`-regels, `BUZZ_REF` tegen de
      relay-tag, `uses:`-regels.
- [ ] 2.5 Vóór de migratie: backup van `auth.db*`, `push_subs.json` en de
      relay-`.env`; `COMPOSE_PROJECT=buzz-prod`, en met `docker volume ls`
      nagaan dat compose de bestaande volumes gebruikt.
- [ ] 2.6 **Marks installatie migreren** volgens
      `docs/how-to/migreren-naar-compose.md`. Het moment kiest Mark.
- [ ] 2.7 Nameten: inloggen, bericht sturen, push ontvangen,
      `chat/e2e/api.sh` tegen de tailnet-URL; `ss -ltnp` op de VM toont alleen
      loopback.
- [ ] 2.8 Na een week zonder terugval: homelab-PR die
      `ansible/files/boomhuis-chat.service` weghaalt en `docker/buzz-relay/`
      vervangt door een verwijzing naar `deploy/` (het playbook dat `.env`
      zaait gaat mee); `/opt/buzz-build/chat` opruimen; `chat/README.md` en
      `docs/how-to/inloggen.md` noemen `/opt/buzz-build` niet meer.

## 3. Regelgrens in CI

- [x] 3.1 Check-script (bare, ≤ 200 regels, SPDX-header): scope `*.py *.js
      *.sh *.css *.html Dockerfile`; uitgezonderde categorieën met reden;
      baseline met de huidige overschrijdingen.
- [x] 3.2 `verify.sh` draait de check.
- [x] 3.3 `.github/workflows/verify.yml`: op PR en push naar `main`; Python via
      `uv` met pyyaml; actions per SHA.
- [ ] 3.4 Mark: de check verplicht maken voor merge (branch protection).
- [ ] 3.5 Splitsen en van de baseline halen: `agents/test_topology.py`,
      `chat/server.py`, `chat/buzzcli.py`, `chat/app.css`,
      `agents/test_sessies.py`.
- [x] 3.6 `CLAUDE.md` en `openspec/project.md`: scope van de regel, en dat CI
      hem handhaaft.

## 4. Security-review van de auth-stack

- [ ] 4.1 Aparte review-sessie op `chat/auth.py`, `auth_store.py`,
      `auth_routes.py`, `adminctl.py` en de cookie-, CSRF- en
      `X-Forwarded-For`-afhandeling in `server.py`. Alleen findings met
      reproduceerbaar pad.
- [ ] 4.2 Verdict als baton in `handover/`; High en Medium gefixt en nagemeten.
- [ ] 4.3 `chat/auth.py` splitsen; de baseline is leeg.

## 5. Poort en afronding

- [ ] 5.1 Pas als 2.7, 4.2 en 4.3 af zijn: chat-package openbaar of een
      eerste installatie bij een derde. Mark beslist.
- [ ] 5.2 Archiveren, na `uitrol-voor-derden`.
