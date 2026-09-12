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
- [x] 1.9 Live: sessies gestart vanuit de chat noemen starter én aanvrager in de
      startpost, en het runbestand heet naar de aanvrager. Bewezen bij PR #102,
      #105, #106 en #110 — alle vier uit een `!sessie build` vanuit #bouw.

## 2. Eén uitrolpad, pin in git

- [x] 2.1 `deploy/docker-compose.yml`: elk `image:` letterlijk, zonder
      variabele; drijvende tags naar minstens major.minor.
- [x] 2.2 `CHAT_IMAGE` en `BUZZ_IMAGE` uit `deploy/.env.example`;
      `docs/how-to/installeren.md`: een upgrade is een nieuwe compose-versie.
- [x] 2.3 `.github/workflows/chat-image.yml`: actions per commit-SHA.
- [x] 2.4 Pin-check (onderdeel van 3.1): `image:`-regels, `BUZZ_REF` tegen de
      relay-tag, `uses:`-regels.
- [x] 2.5 Gedaan vóór de migratie: `docker-compose.yml.pre-chat` en
      `.env.pre-chat` als backup, `COMPOSE_PROJECT=buzz-prod`, en het oude
      volume is gekopieerd in plaats van verplaatst — het staat er nog.
- [x] 2.6 Marks installatie is gemigreerd (2026-09-11) en draait sindsdien uit
      een gepind image; inmiddels op 0.7.0.
- [x] 2.7 Nagemeten, en strenger dan gevraagd: niet alleen `api.sh` maar alle
      drie de uitrol-lagen (`after-deploy.sh`), bij elke uitrol sindsdien. `ss
      -ltnp` toont chat op loopback en de relay op het LAN — dat laatste is
      bewust, agent-lxc praat daarmee.
- [x] 2.8 Uitgesplitst naar de change `opruimen-na-migratie`: het oude pad
      opruimen kan pas ná een week zonder terugval, en een change openhouden om
      een kalender af te wachten maakt de lijst onbetrouwbaar.

## 3. Regelgrens in CI

- [x] 3.1 Check-script (bare, ≤ 200 regels, SPDX-header): scope `*.py *.js
      *.sh *.css *.html Dockerfile`; uitgezonderde categorieën met reden;
      baseline met de huidige overschrijdingen.
- [x] 3.2 `verify.sh` draait de check.
- [x] 3.3 `.github/workflows/verify.yml`: op PR en push naar `main`; Python via
      `uv` met pyyaml; actions per SHA.
- [x] 3.4 De check verplicht maken voor merge. **Niet via branch protection**:
      GitHub biedt protected branches en rulesets op een PRIVATE repo alleen
      onder een betaald plan (gemeten 2026-09-12: *"Upgrade to GitHub Pro or make
      this repository public"*). In plaats daarvan `scripts/install_hooks.sh`:
      een pre-push-guard die `verify.sh` draait vóór een push naar `main`, op de
      machine waar alle pushes vandaan komen. Een guard, geen hek — `--no-verify`
      blijft bestaan. Wil je het wél hard: Pro nemen, of de repo publiek maken.
      Dat is een besluit met een prijs en het is aan Mark.
- [x] 3.5 Gesplitst en van de baseline gehaald (PR #102, #106); baseline leeg: `agents/test_topology.py`,
      `chat/server.py`, `chat/buzzcli.py`, `chat/app.css`,
      `agents/test_sessies.py`.
- [x] 3.6 `CLAUDE.md` en `openspec/project.md`: scope van de regel, en dat CI
      hem handhaaft.

## 4. Security-review van de auth-stack

- [x] 4.1 Aparte review-sessie op `chat/auth.py`, `auth_factors.py`, `auth_store.py`,
      `auth_routes.py`, `adminctl.py` en de cookie-, CSRF- en
      `X-Forwarded-For`-afhandeling in `server.py`. Alleen findings met
      reproduceerbaar pad.
- [x] 4.2a Verdict als baton: `handover/2026-09-12-security-review-auth.md`.
- [x] 4.2b High en Medium gefixt (PR #110) en nagemeten: verify groen, en de
      F3-test faalt aantoonbaar zonder de fix (teruggedraaid gecontroleerd:
      2 van 4 rood). Uitgerold als 0.7.0, drie uitrol-lagen groen.
- [x] 4.3 `chat/auth.py` gesplitst (PR #106); de baseline is leeg.

## 5. Poort en afronding

- [x] 5.1 Het chat-package staat publiek sinds 2026-09-11 (Marks besluit), en de
      poort die deze change eraan hing — review gedaan, High/Medium gefixt,
      auth.py gesplitst — is nu ook gepasseerd. Een eerste installatie bij een
      derde blijft Marks beslissing.
- [x] 5.2 Archiveren, na `uitrol-voor-derden`.
