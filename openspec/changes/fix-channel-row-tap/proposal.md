## Why

Mark, 2026-09-07: *"ik mis nu de input balk"* — hij kon niet posten vanuit
#general.

De invoerbalk was niet weg: de **kanaallade stond open en dekte hem af**. De lade
is `min(78vw, 320px)` breed, dus op een telefoon blijft er van de composer
hooguit de ➤-knop zichtbaar. De lade sluit alleen bij een tik op het
donkere gebied ernaast of bij het kiezen van een kanaal — en juist dat tweede
faalde vaak.

De oorzaak staat in `app.js`: de open-handler hangt aan drie **kind-spans**
(`.cmeta`, `.hash`, `.unread`), niet aan de rij zelf. De rij is een
volledige-breedte flexbox met `padding:.7rem`; alles rechts van de tekst is dus
dood oppervlak. Live gereproduceerd op een iPhone-13-viewport tegen de draaiende
VM:

| tik | resultaat |
|---|---|
| op de kanaalnaam (`.cn`) | kanaal wisselt, lade sluit |
| op de lege ruimte in dezelfde rij | **niets** — lade blijft open, invoerbalk blijft afgedekt |

Bij een korte naam als `#bouw` is dat dode gebied breder dan de tekst zelf. Wie
ernaast tikt, ziet een lade die niet weggaat en een chat zonder invoerbalk.

## What Changes

- **De hele kanaalrij wordt het klikdoel** (`row.onclick`) in plaats van drie
  losse spans. De verwijderknop stopt de propagatie al, dus die blijft werken.
- Geen wijziging aan de lade-CSS, de composer of de endpoints: het dode
  oppervlak was het hele probleem.

## Impact

- `chat/app.js` (kanaalrij-handler), spec `webchat-pwa`.
- Geen server-, relay- of datawijziging. Redeploy van de PWA volstaat.
