# Design: hub-and-spoke-identities

## Besluit 1 — odins sleutel wordt de hub, niet de coordinator-sleutel hernoemd

Eerst geadviseerd: de coordinator-sleutel hernoemen naar `odin`, zodat alle
geschiedenis onder één sleutel blijft.

**Verworpen bij uitvoering.** `identities.yml` sleutelt op handle, en `odin`
bestónd al (aangemaakt 2026-09-07, één bericht). Hernoemen zou dus vragen: de
SOPS-sleutel `coordinator` → `odin` hernoemen, én een verzonnen historische
handle voor de bestaande odin-entry om de botsing op te lossen. Twee statusregels
tegenover een sleutelverhuizing plus een verzonnen naam.

Het argument vóór hernoemen vervalt bovendien: de naam-resolutie leest
`identities.yml` ongeacht status, en de coordinator-entry blijft (ingetrokken)
staan. Zijn acht berichten in #general blijven dus "coordinator" heten. Er gaat
geen spoor verloren; alleen de sleutel wordt niet meer gebruikt.

## Besluit 2 — de hub-regel wordt afgedwongen, niet afgesproken

`ping.sh` weigert een sessie in `#general` met exit 8 en een melding die zegt
waar het bericht dan wél hoort.

**Verworpen: het in de README zetten.** Elke sessie die start leest de conventie
niet, of leest hem en vergeet hem drie uur later. De guard staat naast de
bestaande weigering van de mens-identiteit en van ingetrokken sleutels — dezelfde
plek, dezelfde vorm, dezelfde bewijslast.

**Verworpen: sessies helemaal uit de chat halen** (rapporteren via odin). Dat
lost het lawaai óók op, maar kost het audit-argument van `add-session-identities`:
identiteit = sleutelpaar, elk bericht toewijsbaar aan de echte afzender. Sessies
mogen best praten — alleen niet in het kanaal dat voor de mens en zijn hub is.

## Besluit 3 — `archivaris` vervalt

Die had als enige uitsluitend `#general`. Besluit Mark, 2026-09-07: *"archivaris
mag weg, geen chat-facet meer."* Omdat zijn chat-facet zijn énige facet was
(`executie: null`), valt "geen chat-facet" hier samen met "geen agent"; de
definitie is verwijderd (handbook#15).

Dat kostte niets aan draaiende functionaliteit: hij had geen entry in
`identities.yml`, stond niet in de listener-run-lijst, en `chat/roster.py`
noteerde al dat hij nergens draaide. `_live.md` toonde hem wél als draaiende
chat-agent — die lijst leest de handbook-registry en niet wat de listener
werkelijk spawnt. Dat gat blijft bestaan en is een eigen change waard.
