# Design — technical-debt-11-09

Drie punten uit de architect-review in #technical_debt (2026-09-11), met één
draad: een regel die alleen in proza bestaat, drijft af. De review gaf per punt
de richting: (1) `aanleiding` meegeven, odin alleen namens mensen op `starters`;
(2) *beslist*: Marks installatie mee in dezelfde migratie, vóór de eerste derde;
(3) een regel-check of de conventie bewust aanpassen, `auth.py` apart reviewen.
Hieronder per punt: wat er is (met vindplaats), wat we kiezen, wat afvalt.
Nagemeten op `main` (57492a5) en op de open PR #71, die op punt 1 en 2 meebeweegt.

## 1. Werksessies: starter én aanleiding

**Wat er is.** `agents/listener.py` roept `probeer_sessie` op twee plekken aan:
met `schrijver` voor een marker die een mens zelf typt, met `handle` voor een
marker in een agent-antwoord. In dat tweede geval is de schrijver van het
aansturende bericht bekend, maar wordt niet doorgegeven. `agents/sessies.py`
gebruikt die ene `wie` voor machtiging, limiet, bestandsnaam en startpost.

De listener laat nooit een agent op een agent reageren (`AGENT_PUBS`), dus het
aansturende bericht komt nooit van een listener-agent. Dat is niet hetzelfde als
"van een mens": `orchestrator` en de `rol: sessie`-identiteiten zijn óók geen
listener-agent, en PR #71 zet `orchestrator` op `starters`.

**Gekozen.**

- Twee rollen per sessie. De **starter** schreef de marker (odin, of de mens
  zelf); de **aanleiding** is de Nostr-afzender van het bericht dat de beurt in
  gang zette. Typt een mens de marker zelf, dan zijn ze gelijk.
- Machtiging: starter op `starters`, aanleiding op `starters`, en de aanleiding
  heeft `rol: mens` in `identities.yml`. Die derde voorwaarde is wat "namens
  mensen" mechanisch betekent; de registry draagt `rol` al.
- De limiet gaat per aanleiding, niet per starter. Met odin als tussenpersoon zou
  een limiet per starter de tweede persoon weigeren die odin iets vraagt. Het
  risico waarvoor de oude regel bestond — een agent die in een lus elke beurt een
  sessie start — vervalt: elke sessie vergt nu een mensbericht als aanleiding, en
  `max_gelijktijdig` blijft.
- Vastleggen op drie plekken: bestandsnaam `{typ}-{aanleiding}-{ts}.jsonl`; een
  eerste regel in het runbestand (`"type": "boomhuis_sessie"`, starter,
  aanleiding, bericht-id, kanaal), geschreven vóór het proces start — de oogst
  slaat onbekende types al over; en de startpost "gestart door @odin namens
  @mark".
- `prompts.sessie_clausule` krijgt de aanleiding mee, zodat odin alleen hoort over
  types die voor déze persoon startbaar zijn. Anders kondigt odin een sessie aan
  die meteen een ⛔ krijgt.

**Verworpen.**

- *Alleen loggen, machtiging ongewijzigd.* Dicht het auditgat, niet de omweg.
- *Agents van `starters` af; alleen mensen typen de marker.* Veiligst en
  simpelst, maar het schrapt precies wat Mark vroeg in
  `werksessies-vanuit-de-chat`: odin die zelf een sessie opspint.
- *Odin schrijft `namens @x` in de marker.* Identiteit uit tekst; de bestaande
  eis verbiedt dat, en odins tekst is te sturen door alles in odins context.
- *`orchestrator` toestaan als vertrouwde automatisering.* Die sleutel staat op
  agent-lxc en wordt gedeeld door dispatch, jobs en terminal-sessies. Een sessie
  met aanleiding `orchestrator` heeft hetzelfde gat als een met aanleiding
  `odin`: er is geen mens te herleiden. Automatisering die een sessie wil, is een
  job. Van alle keuzes hier is dit de makkelijkst om te draaien in de review.

**Wat dit niet oplost.** De aanleiding is zo goed als de Nostr-afzender, en de
webchat tekent elk bericht met Marks sleutel (`chat/actions.py`; design van
`inloggen-per-persoon`). Nodigt Mark iemand uit in de eigen installatie, dan is
die persoon voor de listener `mark` en komt door elke check hierboven. De
oplossing is een relay-identiteit per persoon (`identity-registry`), een eigen
change. Tot dan zijn werksessies alleen sluitend zolang Marks installatie één
persoon heeft; de how-to zegt dat hardop. Voor derden speelt het niet: de
listener hoort niet bij hun installatie.

## 2. Eén uitrolpad, met de pin in git

**Wat er is.** Marks chat draait als `boomhuis-chat.service` uit
`/opt/buzz-build/chat`, gevuld met `scp`. De relay draait in compose vanuit de
homelab-repo met `image: ${BUZZ_IMAGE:-ghcr.io/block/buzz:main}`: ontbreekt de
env-waarde, dan draait `:main`, en de echte pin staat in `/opt/buzz-relay/.env`
op de host — niet in git. PR #71 neemt in `deploy/docker-compose.yml` die
fallback over, zet `CHAT_IMAGE` ook in `.env`, en houdt drijvende tags
(`postgres:17-alpine`, `redis:7-alpine`, `rclone/rclone:1`). Het migratiepad
staat in PR #71 (`docs/how-to/migreren-naar-compose.md`), maar "uitvoeren pas na
Marks go".

**Gekozen: Marks installatie gaat als eerste over het nieuwe pad.** Het besluit
komt uit de review; de redenen:

- Twee uitrolpaden lopen uiteen, en het pad dat elke dag draait is dan het pad
  dat niemand tegen de spec houdt. Zo stond de relay-poort op `0.0.0.0` terwijl
  de spec "alleen tailnet" zei.
- Alleen Marks installatie heeft echte staat: accounts, push-registraties,
  relay-volumes onder project `buzz-prod`. Een schone VM bewijst installeren;
  alleen een migratie bewijst upgraden, en elke derde gaat ooit upgraden.
- Vóór de eerste derde betekent: een fout in het compose-pad raakt eerst Mark.

Het moment kiest Mark (de chat ligt enkele minuten stil); óf het gebeurt is niet
langer optioneel. `uitrol-voor-derden` is pas archiveerbaar als Marks chat uit
het image draait.

**Gekozen: de pin staat letterlijk in het compose-bestand.** Elk `image:` in
`deploy/docker-compose.yml` is een letterlijke waarde, zonder variabele of
fallback. `.env` bevat secrets, bind-adressen en de projectnaam, geen images.
Toegestaan: een commit-SHA (`sha-…`), een digest, of een versie met minstens
major en minor (`17.6-alpine`, niet `17-alpine`). `BUZZ_REF` in `chat/Dockerfile`
wijst naar dezelfde upstream-commit als de relay-tag — dat staat nu alleen als
commentaar in dat bestand.

**Verworpen.**

- *`${BUZZ_IMAGE:-…:main}`* (homelab nu, PR #71): een vergeten env-waarde levert
  stil een drijvende tag. Precies het geval waarvoor de regel bestaat.
- *`${CHAT_IMAGE:?}` uit `.env`* (PR #71): geen drijvende fallback, maar bij Mark
  staat `.env` op de host omdat er secrets in staan. De pin is dan niet in git, en
  wat draait en wat de repo zegt lopen spoorloos uiteen.
- *Default in compose, override in `.env`*: git toont een pin die misschien niet
  draait.
- *Een aparte, gecommitte `versies.env`*: pin in git, maar een tweede bestand en
  een tweede `--env-file` voor wat één letterlijke regel ook doet. Een derde krijgt
  het compose-bestand toch per release; een andere versie is een diff in de eigen
  kopie.
- *Overal digests*: het meest onveranderlijk, maar een diff van `sha256:3f…` zegt
  een reviewer niets. Dat een semver-tag upstream opnieuw gepusht kan worden,
  accepteren we, zoals de conventie nu al doet.

**Handhaving.** De check uit punt 3 leest ook `deploy/docker-compose.yml` en
`chat/Dockerfile`: rood op een `image:` met variabele, zonder tag, met
`latest`/`main` of met alleen een major, en als `BUZZ_REF` en de relay-tag uiteen
lopen. Dezelfde check eist commit-SHA's voor `uses:` in `.github/workflows/`:
`chat-image.yml` uit PR #71 bouwt met `@v3`/`@v4`, en een gepind image uit een
drijvende build is maar de halve regel.

## 3. De 200-regelgrens: handhaven, met expliciete scope

**Wat er is.** Boven de 200 op `main`: `agents/test_topology.py` (241),
`chat/app.css` (230, niet in de review), `chat/server.py` (221),
`chat/buzzcli.py` (210), `chat/auth.py` (203). PR #71 voegt
`agents/test_sessies.py` (215) en `deploy/docker-compose.yml` (201) toe. Geen CI.
Waar de regel wél werd toegepast, gaf hij een betere indeling (`relay.py` uit
`listener.py`; `auth_store.py` en `auth_routes.py` naast `auth.py`). De
overschrijdingen wijzen op gemengde verantwoordelijkheden: `test_topology.py`
test vier modules, `do_GET` in `server.py` is een if-ladder van 95 regels.

**Gekozen.**

- **De grens blijft 200; de scope wordt expliciet**: code die we zelf schrijven —
  `*.py`, `*.js`, `*.sh`, `*.css`, `*.html`, `Dockerfile` — tests inbegrepen.
  Niet: Markdown, `LICENSE`, binaire bestanden, YAML/JSON-data en vendored
  configuratie. `deploy/docker-compose.yml` is een vendored upstream-kopie plus
  één service; opknippen breekt de diff tegen upstream waar de kop op leunt.
- **De check zit in `verify.sh`, CI draait `verify.sh`.** Eén workflow op elke PR
  en push naar `main`: unittests, regelgrens, pins. Python via `uv` (de
  agents-tests vergen pyyaml), actions per SHA. De check verplicht maken voor
  merge is een repo-instelling, dus aan Mark.
- **Een tijdelijke baseline.** De check begint met de huidige overschrijdingen
  (pad plus aantal regels) in het script. Een baseline-bestand mag niet groeien;
  een nieuw bestand mag niet over de 200. De change is niet archiveerbaar met een
  niet-lege baseline. Zo staat de drift stil vanaf de eerste groene run, zonder
  op de security-review te wachten.
- **Splitsen langs verantwoordelijkheid**, niet door regels weg te knippen:
  `test_topology.py` per geteste module, leesroutes uit de handler in
  `server.py`, roster-functies uit `buzzcli.py`, `app.css` per schermdeel,
  `test_sessies.py` per onderwerp. `auth.py` als laatste, ná de review, zodat die
  de code ziet die live gaat.

**Verworpen.**

- *Pre-commit-hook.* Draait alleen waar hij geïnstalleerd is. Verse clones,
  habitat- en agent-worktrees (zoals die waarin deze change geschreven is) hebben
  hem niet, en `--no-verify` slaat hem stil over. Lokaal handhaven hebben we nu.
- *Alleen `verify.sh` uitbreiden, zonder CI.* `verify.sh` bestaat al, en de regel
  dreef toch af. Een check die niemand hoeft te draaien, is geen check.
- *De grens naar 250, of laten vallen.* De overschrijdingen zijn 3 tot 41 regels,
  en waar de regel werd toegepast leverde hij iets op. Verruimen verschuift alleen
  waar de drift begint; de druk is de bedoeling.
- *Een permanente uitzonderingslijst.* Daar eindigt een regel ongemerkt. Blijvende
  uitzonderingen zijn categorieën (Markdown, vendored), geen losse bestanden.
- *Eerst alles splitsen, dan de check aan.* Dan staat de deur open zolang de
  review duurt; PR #71 liet zien hoe snel dat gaat.

**Security-review van de auth-stack.** `auth.py` bevat eigen scrypt-parameters,
TOTP (RFC 6238 met `hmac`) en sessietokens; `auth_store.py` sessies en
uitnodigingen; `auth_routes.py` de rem, CSRF en cookies. Zelf schrijven was een
bewuste keuze (stdlib, leesbaar), maar betekent ook: geen upstream die er al op
aangevallen is. De review van 2026-08-30 dateert van vóór deze code.

Gekozen: een aparte review-sessie op de hele auth-stack — ook `auth_routes.py` en
`server.py`, want daar zitten de rem, `X-Forwarded-For` en de cookie-vlaggen. In
de vorm van 2026-08-30: alleen findings met reproduceerbaar pad en nagemeten fix,
het verdict als baton in `handover/`. Poort: geen derde met een open High of
Medium.

Verworpen: *`/security-review` op de diff van deze change* — die kijkt naar
openstaande wijzigingen, en de auth-code staat al op `main`. *Nu een externe
audit* — past bij een product met klanten, niet bij de eerste installatie; kan
later, met deze review als nulmeting.

## Volgorde

Check in CI met baseline (de drift staat stil) → werksessies (los van de rest) →
letterlijke pins, dan Marks migratie → security-review, fixes, `auth.py`
splitsen (baseline leeg) → de poort gaat open; dat beslist Mark.
`uitrol-voor-derden` wordt eerst gearchiveerd: deze delta op `relay-deployment`
bouwt op de eisen daarvan.
