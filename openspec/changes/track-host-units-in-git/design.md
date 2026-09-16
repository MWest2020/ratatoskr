# Design

## Mandaat

Deze change sluit de drift tussen git en host voor systemd-units. Hij herontwerpt
de credential-rotatie niet; daarvan wordt alleen de sluitvoorwaarde vastgelegd.

## Op welke machine de omgekeerde check hoort te draaien

Op déze machine. Beide units zijn **user**-scope en staan in
`~/.config/systemd/user/`. Dat is direct nagekeken, niet afgeleid uit
`systemctl` in de system-scope — die eerdere lezing was fout, en precies de fout
die deze change afsluit.

De omgekeerde check draait dus naast de bestaande voorwaartse check, tegen
dezelfde map. Overwogen en verworpen: hem elders draaien en hoststatus over ssh
ophalen. Dat maakt een gate die fail-closed moet zijn afhankelijk van
bereikbaarheid, en dan slaat hij stil over in plaats van te falen.

## Unit én script horen bij elkaar

`claude-secret-refresh.service` draait `%h/refresh-claude-secret.sh`. Daar zit
het gedrag: lezen van `~/.claude/.credentials.json`, ssh naar `cp-01`, het secret
herschrijven in namespace `agents`. De unit zonder het script levert een
verwijzing naar niets.

Daarom gaan ze samen naar `orchestrator/systemd/`, en daarom is de security-gate
zwaarder dan bij een gewone unit: niet alleen de unit-files, maar het script met
zijn echte schrijfpad naar een cluster-node.

## Waarom een tweede schrijver een probleem is

Habitat `add-dispatch` taak 4.2 legt vast: het subscription-token verloopt na
~8 uur, en de **orchestrator is de énige schrijver** van
`claude-credentials`, juist om een rotatie-race uit te sluiten. Workers
verversen nooit zelf.

Een vier-uurlijkse timer op deze host is een tweede schrijver op datzelfde
secret. Dat is niet slordig — het is in strijd met het besluit dat de race moest
uitsluiten. Vandaar een sluitvoorwaarde en een toetsdatum in plaats van "staat
er nu eenmaal".

## Uitzonderingen met een reden, geen allowlist

`zettelkast-daily.{service,timer}` staat hier geïnstalleerd en hoort bij
MWest2020/zettelkast. Zonder uitzondering meldt de nieuwe check vanaf dag één
iets wat geen fout is, en dan zet iemand hem uit — dat is hoe een gate sterft.

De uitzondering draagt daarom de **reden en de herkomst-repo**. Wie er later
naar kijkt ziet of de uitzondering nog klopt. Een kale lijst namen kan dat niet.
