---
status: current
last_reviewed: 2026-10-23
---

# Een werksessie starten vanuit de chat

Een chat-beurt is één `claude -p` van hoogstens 180 seconden met `Read/Grep/Glob`.
Genoeg voor een gesprek, te klein voor werk. Een **werksessie** is dezelfde
machinerie met minuten in plaats van seconden, een eigen werkmap en een eigen
toolset — en hij post zijn resultaat in het kanaal waar hij gestart is.

## Starten

Zet in een kanaal een regel:

```
!sessie zettelkast wat moet er nog met de gedeelde clips gebeuren?
```

Wat er dan gebeurt:

1. de listener herkent de marker, kijkt of jij dit type mag starten, en post
   `▶️ sessie gestart` met het tijdbudget;
2. tussentijds verschijnen een paar regels `⋯ sessie zettelkast: Grep …` zodat
   je ziet dat er iets gebeurt;
3. aan het eind komt het antwoord, met een voetregel: looptijd, kosten, beurten.

Een agent kan het ook zelf: schrijft odin de marker in zijn antwoord, dan wordt
die regel uit het geposte bericht geknipt en start de sessie. Zo kun je vragen
"odin, laat een sessie hiernaar kijken" in plaats van het commando zelf te typen.

**Wie start, en namens wie.** Een sessie kent twee rollen. De *starter* schreef de
marker; de *aanvrager* is wie het bericht stuurde dat die beurt in gang zette.
Typ je 'm zelf, dan zijn ze gelijk. Vraagt odin er een voor jou, dan staat er
"gestart door @odin namens @mark", en het runbestand heet ook naar jou — anders
heet elke door odin gestarte sessie odin en is achteraf niet te zien voor wie hij
liep. Beide moeten bij het type op `starters` staan; de limiet van één lopende
sessie geldt **per aanvrager**, zodat twee mensen tegelijk iets aan odin kunnen
vragen.

`orchestrator` staat bewust op `starters` (besluit Mark, 2026-09-11). Wat dat
kost: die sleutel wordt gedeeld door dispatch, jobs en terminal-sessies, dus bij
een sessie met `orchestrator` als aanvrager stopt de herleiding bij
"automatisering op agent-lxc" en niet bij een persoon.

De chat blijft gewoon werken terwijl een sessie loopt — hij draait losgekoppeld.

## Wat een sessie mag

Er zijn twee soorten, en dat staat per type in `sessions.yml`.

**Lezende sessies** (`zettelkast`, `skill-forge`, `ratatoskr`, `wordsworth`,
`wanderer`, `research`) lezen en verder niets. Geen `Write`, geen `Edit`, geen `Bash`, geen push; de lees-tools zijn
pad-begrensd tot de werkmap van het type. Concluderen ze dat er iets moet
veranderen, dan **stellen ze dat voor**.

**Schrijvende sessies** (`build`, `writes: true`) krijgen een **verse
git-worktree van `origin/main` op een eigen branch**, buiten elke draaiende
checkout, en mogen daarbinnen schrijven, `git` draaien en tests draaien. Ze
eindigen met een **pull request** en posten de link in het kanaal.

Wat ze niet kunnen: naar `main` pushen. Dat is geen afspraak maar een hek — er
staat een `pre-push`-hook in de worktree die alles behalve de eigen branch
weigert. Reden: een schrijvende sessie heeft `Bash` nodig, en dan is "push niet
naar main" in een prompt niets waard; alles wat in zijn context komt — een
README, een issue, een opgehaalde pagina — kan die instructie sturen. Een hook
kan dat niet.

Mergen blijft mensenwerk, en de poortwachter van de habitat-brug (`!dispatch`)
verandert niet: dat is de weg voor gekooide runs, dit is de lichte weg ernaast
met een voorstel als uitkomst.

Schrijven is een **apart recht**: `build` heeft zijn eigen `starters`-lijst, dus
wie `zettelkast` mag starten mag daarmee nog niet bouwen.

## Types

Alle types staan in [`agents/sessions.yml`](../../agents/sessions.yml): werkmap,
tools, model, tijdbudget, wie mag starten, en onder welke identiteit het
resultaat gepost wordt. Een nieuw type is een PR op dat bestand, geen
prompt-truc.

| type | werkmap | doet |
|---|---|---|
| `zettelkast` | `~/zettelkast` | leest de vault en beoordeelt wat er met gedeelde clips moet gebeuren |
| `skill-forge` | `~/skill-forge` | legt materiaal naast de eigen skill-bibliotheek |
| `ratatoskr` | de listener-checkout | leest deze repo en levert een onderbouwd voorstel |
| `wordsworth` | `~/wordsworth` | leest de PII-pijplijn en toetst een vraag aan code én metingen |
| `wanderer` | `~/Wanderer` | leest de scanner en het regelpack, inclusief de afgewezen ADR's |
| `research` | `~/research` | zoekt iets op het **open web** op en meldt terug mét bronvermelding |
| `build` | een verse worktree | **schrijft**, draait tests, opent een pull request |

De laatste twee zijn er sinds 2026-09-21 en hebben geen schrijvende tegenhanger:
`build` bestaat alleen voor ratatoskr. Een chatbericht dat pull requests opent in
twee andere repo's is een groter recht dan wat hier gevraagd werd; dat is een
regel extra in `sessions.yml` zodra iemand het wil.

Hun tijdbudget is 30 minuten in plaats van 15. Een repo-brede leessessie is
trager dan een vault-scan, en een half rapport is geen rapport.

Het systeembericht verschilt per type, want de contracten verschillen: bij
wordsworth de harde invariant (geen klare PII richting de index) en de vraag
"verandert dit een belofte?", met de instructie een bewering aan de **code** te
toetsen en niet aan de spec alleen — dat is daar in beide richtingen misgegaan.
Bij Wanderer dat de moat het regelpack is en niet de scanners, en dat de
**afgewezen** ADR's er ook bij horen: een voorstel dat een gesloten besluit
heropent, hoort te zeggen waarom dat besluit niet meer geldt.

## De hub blijft vrij

`research` bestaat omdat de hub het werk niet zelf hoort te doen. Odin krijgt een
link of een vraag, zet er een sessie op en is meteen weer aanspreekbaar; het
antwoord komt terug in het kanaal, onder odins eigen identiteit — net als bij de
andere types. Dat is het hub-en-spoke-patroon zoals het bedoeld is: de hub
beslist waar iets heen gaat, de spoke doet het werk.

Twee dingen die bij `research` anders zijn:

- **Geen repo.** Zijn invoer is een link of een vraag uit het kanaal, niet een
  checkout. De werkmap `~/research` is een kladmap, zodat de pad-begrensde
  leestools iets hebben om aan gebonden te worden — `Read(./**)` zonder map
  begrenst niets.
- **Het open web.** Geen domeinlijst (besluit Mark, 2026-09-21). Een lijst die je
  eerst moet bijwerken om een link te mógen lezen, is dezelfde soort
  zelf-opgelegde beperking die dit type juist opheft.

Wat dat kost: een opgehaalde pagina is tekst van een vreemde. Staat daar
`!sessie build …` in en citeert de sessie die regel, dan is dat een instructie
van iemand anders. Daarom telt een marker **alleen op de eerste regel van het
eigen antwoord** van een agent; wat verderop staat is geciteerd materiaal en doet
niets. Een mens die de marker onder een zin typt wordt wél gelezen — daar is de
tekst van de persoon zelf. Het verschil is vertrouwen, niet syntax.

## Zonder een naam te noemen

Een kanaal kan een **default agent** aanwijzen (`channels.yml`,
`default_agent:`). Noemt een bericht niemand en valt er ook geen gesprek voort te
zetten, dan gaat het naar die agent. In `#general` is dat odin.

De volgorde is de afspraak, en hij staat in `agents/triggers.py`: **mention >
vervolg > default**. Wie een agent noemt krijgt die agent, ook als een andere net
sprak; pas als er niemand genoemd is en er niets loopt, gaat het naar de default.

Opt-in per kanaal, met opzet. In een feed als `#statistics` zou een agent die op
elke regel antwoordt ruis zijn met een prijskaartje. Een `default_agent` die niet
in dat kanaal mag spreken **laat de listener niet starten** — stil overslaan ziet
er van buiten uit als een listener die niet draait.

## Grenzen

- **Tijdbudget** per type (`zettelkast`: 15 min). Erover → de sessie wordt
  gestopt en meldt dát, met wat er tot dan gedaan is.
- **Hoogstens twee sessies tegelijk**, en één per aanvrager. Vraag je een tweede
  terwijl de eerste loopt, dan krijg je dat te horen.
- **Een stille sessie bestaat niet.** Faalt hij, of komt hij leeg terug, dan
  staat de reden in het kanaal. Anders leest een storing als "niets gevonden".

## Als het niet werkt

- `⛔ geen sessie: onbekend sessietype …` — de listener noemt de types die er
  wél zijn; check `agents/sessions.yml`.
- `⛔ geen sessie: @naam mag het type niet starten` — zet jezelf bij `starters`
  van dat type (PR).
- Niets gebeurt na een marker: draait de listener met deze code? De marker wordt
  alleen gelezen door `agents/listener.py`, niet door de webchat.

## The marker counts on the first line only

An agent's own `!sessie` (and `!build`, `!role`, `!channel`, `!close`)
counts only on the **first** line of its answer. A quoted page further down
must never start anything. Until 2026-10-23 the prompt told agents to use the
**last** line. Odin did that, the listener dropped the marker without a word,
and odin told Mark a session had started when none had. Since then:

- **The prompt says "first line".**
- **A misplaced marker is said in the channel:** `⚠ \`!sessie\` was not on
  the first line of this answer, so nothing was started.`

## A session odin started wakes odin

Odin often starts a session and plans to do something with its report:
consult architect, build a change. The report is posted under odin's own
name, and the listener never gives a turn on an agent's message, so until
2026-10-23 that plan never fired. Now, when a session odin started finishes,
the listener gives odin **one** follow-up turn in that channel, with the
report as the last message (`agents/session_followup.py`). In that turn odin
may consult or build, but not start another session. A session that wakes a
turn that starts a session would be a loop. A session cut off by its time
budget does not wake odin; its partial work is already in the channel.

## Sessions read the handbook from main

The ratatoskr, wordsworth and wanderer sessions may also read
`~/.worktrees/handbook-read/docs` (`also_reads` in `agents/sessions.yml`).
Before every session starts, `agents/handbook_read.py` moves that worktree to
handbook `origin/main`, so a session never reads a stale copy. On 2026-10-23
`~/handbook` itself was 14 commits behind. If the refresh fails, the session's
start line says so (`⚠ handbook docs not refreshed: …`).

