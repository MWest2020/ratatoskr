---
status: current
last_reviewed: 2026-09-10
---

# Een werksessie starten vanuit de chat

Een chat-beurt is één `claude -p` van hoogstens 150 seconden met `Read/Grep/Glob`.
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

**Lezende sessies** (`zettelkast`, `skill-forge`, `ratatoskr`) lezen en verder
niets. Geen `Write`, geen `Edit`, geen `Bash`, geen push; de lees-tools zijn
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
| `build` | een verse worktree | **schrijft**, draait tests, opent een pull request |

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
