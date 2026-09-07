## Why

Mark, 2026-09-07: *"invoerveld weer weg. dat kan echt niet."* — nadat
`fix-channel-row-tap` de kanaallade al van de composer af had gehaald.

Tweede, andere oorzaak. De app-shell is `body{height:100dvh}`. `dvh` is een
**layout**-eenheid: hij volgt het tonen en verbergen van browser-UI, maar **niet
het toetsenbord**. Opent het toetsenbord, dan krimpt alleen de *visuele* viewport;
de shell blijft even hoog en de invoerbalk — het laatste flex-kind — zakt eronder.
Precies het "weer weg"-gedrag: hij verdwijnt op het moment dat je wilt typen.

## What Changes

- **Een inline-script spiegelt `visualViewport.height` naar `--app-h`**, en de
  body gebruikt die als hoogte (`height:100dvh; height:var(--app-h, 100dvh)`).
  Zonder `visualViewport` blijft het huidige gedrag staan.
- **`interactive-widget=resizes-content`** in de viewport-meta, zodat browsers die
  het ondersteunen de layout-viewport zelf al meeverkleinen.
- Ondergrens van 200px op de meting: een onzinnige waarde mag de shell nooit
  dichtklappen.
- Service-worker-cache naar `v6`, zodat toestellen de nieuwe shell echt krijgen.

## Waarom inline en niet een eigen module

Een nieuw JS-bestand vergt een route in `server.py` en dus een herstart van
`boomhuis-chat` op de VM. Het script is twaalf regels en hoort bij de shell; het
inlijnen houdt de uitrol een bestandskopie zonder herstart, en `app-ui.js` onder
de 200-regelgrens.

## Impact

- `chat/index.html`, `chat/app.css`, `chat/sw.js`. Geen backend-, relay- of
  datawijziging, geen herstart.
