# Design: listener-membership

## Union, geen vervanging

De target-regel wordt `handbook-scope OF relay-lid`, niet alleen relay-lid. Reden:
de handbook blijft de bron voor de *bedoelde* scope van een agent, en een agent
die (nog) geen relay-call oplevert (relay traag/onbereikbaar) blijft in z'n
def-kanalen werken. Relay-lidmaatschap is een ADDITIEVE reden om te reageren —
zo koppelt lid-worden (pop-up, coordinator-default, backfill) aan aanspreekbaar
worden, zonder regressie op wat vandaag al werkt.

## Cache i.p.v. een relay-call per bericht

De poll-lus draait elke ~5s over alle kanalen. Lidmaatschap en de kanaal-lijst
veranderen zelden, dus beide worden ~60s gecachet (`topology.py`). Zo blijft het
aantal `buzz channels members`-calls laag, ook met tientallen kanalen. Een lege
of mislukte fetch overschrijft géén goede cache (val-terug op wat we hadden),
net als bij `roster.identity_map`.

## Live kanaal-set met `channels.yml` als vangnet

`buzz channels list` geeft alle open kanalen; daarmee poll't de listener ook
kanalen die na deploy zijn aangemaakt. Faalt die call, dan valt de poll-set terug
op `channels.yml` (nooit leeg). Bij succes: union van beide (yml-namen blijven
staan, relay vult aan), zodat een hernoemd/ontbrekend relay-record een bekend
kanaal niet stilletjes laat wegvallen.

## I/O via een meegegeven `run`-callable

`topology.py` doet zelf geen subprocess: de listener bezit de buzz-env (nsec,
relay-url) en geeft een `run(args) -> stdout|""`-functie mee. Zo blijft topology
puur (geen env-afhankelijkheid, triviaal te testen) en houdt de listener één
plek waar relay-I/O gebeurt.

## Leesbaarheid: waarom niet de handbook-def aanpassen

Alternatief was coordinator's handbook op `channels: [<alle>]` zetten. Afgewezen:
die lijst loopt achter zodra er een kanaal bijkomt (onderhoudslast), het is een
handbook-wijziging (CODEOWNERS = Mark, human-gate) per nieuw kanaal, en het lost
niet op dat toegevoegde agents aanspreekbaar moeten worden. Relay-lidmaatschap is
de bestaande, bijgewerkte bron van waarheid — de listener hoort die te volgen.
