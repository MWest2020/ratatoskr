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

De chat blijft gewoon werken terwijl een sessie loopt — hij draait losgekoppeld.

## Wat een sessie mag

Lezen. Meer niet. Geen `Write`, geen `Edit`, geen `Bash`, geen push, en de
lees-tools zijn pad-begrensd tot de werkmap van het type. De omgeving is
gestript: geen nsecs, geen tokens.

Concludeert een sessie dat er iets moet veranderen, dan **stelt hij dat voor**.
Veranderen loopt via een OpenSpec-change en een habitat-run; de poortwachter van
de brug (`!dispatch`, alleen door Mark) blijft daarvoor de enige weg.

## Types

Alle types staan in [`agents/sessies.yml`](../../agents/sessies.yml): werkmap,
tools, model, tijdbudget, wie mag starten, en onder welke identiteit het
resultaat gepost wordt. Een nieuw type is een PR op dat bestand, geen
prompt-truc.

| type | werkmap | doet |
|---|---|---|
| `zettelkast` | `~/zettelkast` | leest de vault en beoordeelt wat er met gedeelde clips moet gebeuren |

## Grenzen

- **Tijdbudget** per type (`zettelkast`: 15 min). Erover → de sessie wordt
  gestopt en meldt dát, met wat er tot dan gedaan is.
- **Hoogstens twee sessies tegelijk**, en één per starter. Vraag je een tweede
  terwijl de eerste loopt, dan krijg je dat te horen.
- **Een stille sessie bestaat niet.** Faalt hij, of komt hij leeg terug, dan
  staat de reden in het kanaal. Anders leest een storing als "niets gevonden".

## Als het niet werkt

- `⛔ geen sessie: onbekend sessietype …` — de listener noemt de types die er
  wél zijn; check `agents/sessies.yml`.
- `⛔ geen sessie: @naam mag het type niet starten` — zet jezelf bij `starters`
  van dat type (PR).
- Niets gebeurt na een marker: draait de listener met deze code? De marker wordt
  alleen gelezen door `agents/listener.py`, niet door de webchat.
