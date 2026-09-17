---
status: current
last_reviewed: 2026-09-17
---

# Het werk-overzicht

Een bord in de app met vijf kolommen — *backlog · proposal · building · review ·
merged* — dat één vraag beantwoordt: **wat beweegt er, en wat zit vast?**

Open het met de knop **📋 Board** in de kop.

## Wat je ziet

Bovenaan staat of er iets vastzit. Zo niet, dan staat dat er ook — "Nothing is
stuck" is een uitkomst, geen lege pagina.

Elke kaart draagt de repo, een titel, wie eraan werkt, **hoe hij gebouwd wordt**
(`session`, `session (schrijft)`, `pull request`, `openspec`) en **hoe lang hij
al in die kolom staat**. Een lopende werksessie toont er bovendien bij waar hij
op dít moment mee bezig is — de laatste tool-aanroep uit zijn runbestand. Dat laatste is het punt. Dat er twaalf dingen open staan wist je;
dat PR #71 al drie dagen op review wacht terwijl de rest doorstroomt, niet. Staat
een kaart langer dan de drempel van zijn kolom, dan kleurt hij op.

Kaarten met een PR openen die PR. De rest is alleen kijken: **er is geen slepen
en geen statusknop.** Git is de waarheid, het bord is een spiegel. Een kaart
verplaatst doordat je een PR merget of een change archiveert.

## Waar de gegevens vandaan komen

| kolom | bron |
|---|---|
| backlog | open GitHub-issues |
| proposal | niet-gearchiveerde OpenSpec-changes in de clones op de host |
| building | draft-PR's, lopende werksessies én de tmux-sessies van deze host |
| review | open PR's die niet in draft staan |
| merged | PR's van de laatste paar dagen |

Drempels en bronnen staan in [`jobs/board.yml`](../../jobs/board.yml). Hoe lang
"te lang" is, is een oordeel dat verandert — dat hoort niet in code.

## Backlog: werk dat nog niet begonnen is

Een open issue is een kaart in *backlog*. Draagt het issue het label
`spec-nodig` of `direct`, dan staat dat merk in de titel — dat verschil bepaalt
wat je ermee moet en dat wil je zien zonder door te klikken. Een issue zonder
zo'n label houdt zijn kale titel; een verzonnen indeling is erger dan geen.

Zonder deze kolom toonde het bord alleen wat al liep, en zei het dus niets op
het moment dat je wilt weten wat er nog moet.

Issues en gemergede PR's worden gecacht (standaard tien minuten). Het bord draait
elke twee minuten en mag daar geen GitHub-aanroep per keer aan kwijt zijn. Een
mislukte verversing toont de oude lijst **met** de mededeling dat hij oud is:
stilletjes iets verouderds als actueel presenteren is het enige antwoord dat hier
echt fout is.

### De tmux-sessies van deze host

Sinds 2026-09-16 staan ook de tmux-sessies op het bord. Daarvoor was het werk
waar de meeste uren in gaan alleen zichtbaar voor wie toevallig aangekoppeld
zat, en moest je vragen wat er liep.

Per sessie zie je drie dingen:

- **naam** — de tmux-sessienaam;
- **project** — de werkmap van de actieve pane. Staat de sessie in de home-map,
  dan is er geen project en staat er `—`; dat is eerlijker dan de mapnaam tonen,
  want die suggereert iets.
- **laatste activiteit** — welk commando er draait en hoe lang geleden die sessie
  iets deed. Is de werkmap opgeruimd, dan zegt de kaart dat erbij: een sessie in
  een verdwenen worktree is meestal een sessie die je kunt sluiten.

Er staat **geen issue-nummer** bij. Dat valt niet betrouwbaar uit een pane af te
leiden, en een verzonnen nummer is erger dan geen nummer.

Zet de bron aan met `tmux: true` onder `sources` in `jobs/board.yml`. Hij staat
standaard uit: dit is de enige bron die de machine zelf ondervraagt in plaats van
een pad uit de config te lezen, en dat hoort een zichtbare keuze te zijn.

## Hoe het gemaakt wordt

Zolang het bord openstaat haalt de app elke 30 seconden een verse momentopname,
en de producent draait elke twee minuten. Je ziet een sessie dus echt vooruitgaan
terwijl hij bouwt.

Dat kan omdat de twee bronnen los staan: sessies liggen lokaal en zijn gratis te
lezen, PR's komen van GitHub en worden tien minuten gecachet. Lukt het verversen
van die cache niet, dan gebruikt het bord de oude — en zegt erbij dát hij oud is.

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
