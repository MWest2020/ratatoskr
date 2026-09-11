---
status: current
last_reviewed: 2026-09-12
---

# Het werk-overzicht

Een bord in de app met vier kolommen — *proposal · building · review · merged* —
dat één vraag beantwoordt: **wat beweegt er, en wat zit vast?**

Open het met de knop **📋 Board** in de kop.

## Wat je ziet

Bovenaan staat of er iets vastzit. Zo niet, dan staat dat er ook — "Nothing is
stuck" is een uitkomst, geen lege pagina.

Elke kaart draagt de repo, een titel, wie eraan werkt en **hoe lang hij al in die
kolom staat**. Dat laatste is het punt. Dat er twaalf dingen open staan wist je;
dat PR #71 al drie dagen op review wacht terwijl de rest doorstroomt, niet. Staat
een kaart langer dan de drempel van zijn kolom, dan kleurt hij op.

Kaarten met een PR openen die PR. De rest is alleen kijken: **er is geen slepen
en geen statusknop.** Git is de waarheid, het bord is een spiegel. Een kaart
verplaatst doordat je een PR merget of een change archiveert.

## Waar de gegevens vandaan komen

| kolom | bron |
|---|---|
| proposal | niet-gearchiveerde OpenSpec-changes in de clones op de host |
| building | draft-PR's + lopende werksessies |
| review | open PR's die niet in draft staan |
| merged | PR's van de laatste paar dagen |

Drempels en bronnen staan in [`jobs/board.yml`](../../jobs/board.yml). Hoe lang
"te lang" is, is een oordeel dat verandert — dat hoort niet in code.

## Hoe het gemaakt wordt

Eén producent, buiten de chat:

    bash jobs/publish-board.sh

Die draait `jobs/board.py` (verzamelen) en zet `board.json` in het datavolume van
de chat. De chat serveert dat bestand op `/api/board` en doet verder niets —
geen clones, geen `gh`, geen GitHub-toegang in de container. Dat is expres: elke
traagheid daar zou anders een trage app worden.

Staan producent en chat op verschillende machines (bij Mark: agent-lxc en de
relay-VM), zet dan `BOARD_SSH` en `BOARD_VOLUME`; op één machine volstaat
`BOARD_OUT`. De timer `ratatoskr-board.timer` draait 'm elke tien minuten.

## Als het bord leeg is

- **"no snapshot yet"** — de producent heeft nog nooit gedraaid. Start de timer,
  of draai `publish-board.sh` met de hand.
- **"This snapshot is N minutes old"** — de producent draait niet meer. Kijk met
  `systemctl --user status ratatoskr-board`.
- **Een gele regel met een leesfout** — één bron deed het niet (meestal `gh`).
  De rest van het bord klopt nog; dat wordt expliciet gemeld in plaats van stil
  weggelaten, want "geen PR's" en "GitHub onbereikbaar" zien er anders identiek uit.
