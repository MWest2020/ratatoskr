# Change: werk-overzicht in de app

## Why

Mark heeft nu een app op zijn telefoon, en die toont chat. Wat er *loopt* staat
verspreid: open PR's op GitHub, niet-gearchiveerde OpenSpec-changes in acht
clones op agent-lxc, lopende werksessies in een register in het geheugen van de
listener, blokkades als losse berichten in #escalatie. De standup-job perst dat
elke ochtend in één tekstbericht — nuttig, maar het is een momentopname die
wegscrollt, en je kunt er niets aan aflezen over wáár je aandacht het meest
oplevert.

Mark, 2026-09-11: *"omdat we nu een app hebben, kunnen we dit ook? visueel een
graph tonen qua werk?"* — en na afweging: *"bord en graph op termijn"*.

Het gaat dus niet om een plaatje maar om één vraag: **wat beweegt er, en wat zit
vast?**

## What Changes

- **Een bord in de app.** Vier kolommen — *voorstel · bouwen · review ·
  gemerged* — met per kaart: repo, titel, wie eraan werkt, hoe lang hij al in
  die kolom staat, en een link naar de PR of de change.
- **Eén producent, één momentopname.** Een terugkerende taak op agent-lxc
  verzamelt wat er is (GitHub-PR's, OpenSpec-changes in de clones, lopende
  werksessies, recente #escalatie-signalen) en schrijft één JSON-bestand in het
  datavolume van de chat. De chat serveert dat achter de sessie; de app tekent
  het. De chat praat zelf niet met acht clones — die staan niet in de container.
- **Ouderdom is het signaal.** Een kaart die drie dagen in *review* staat is de
  interessante kaart. Het bord toont dat, en markeert wat op een mens wacht.
- **De graaf komt later.** Zelfde kaarten, andere weergave. Deze change legt
  de gegevens vast zodat dat een tweede view is en geen tweede verzameling.

## Impact

- Nieuw: `jobs/board.py` (producent), `chat/board.py` (serveren),
  `chat/app-board.js` + CSS in de PWA, een timer.
- Gewijzigd: `chat/statics.py`, `chat/index.html`, `chat/sw.js` (cache-bump).
- Spec: nieuwe capability `werk-overzicht`.
- Nieuwe code is Engels ([ADR-0001](../../../docs/adr/0001-code-in-het-engels.md));
  bestandsnamen hierboven volgen dat.
