# End-to-end-tests van de web-chat

Draaien tegen de **echte VM**, niet tegen een mock. Ze vervangen de unittests niet;
ze vangen wat unittests per definitie missen: uitrol, service worker, viewport,
en of de laag eronder ook echt aan staat.

    bash chat/e2e/api.sh          # HTTP: wat een vreemde NIET mag
    node chat/e2e/inloggen.js     # browser: inloggen, sessie, uitloggen
    node chat/e2e/ui.js           # browser: shell, kanalen, laden, token-modal
    node chat/e2e/xss.js          # regressietest op de GitHub-rendering
    node chat/e2e/deeplink.js     # melding -> juiste kanaal
    node chat/e2e/offline-boot.js # koude start zonder tunnel, en herstel

`ui.js`, `xss.js`, `deeplink.js`, `offline-boot.js` en `inloggen.js` hebben Playwright nodig en een Chromium. Staat Playwright
elders, wijs er dan met `NODE_PATH` naar; `executablePath` bovenaan het script
wijst naar de browser.

    NODE_PATH=~/ergens/node_modules node chat/e2e/ui.js

Alle drie geven exitcode 0 bij succes, dus ze zijn te ketenen.

## Waarom `xss.js` bestaat

De Repos-lade rendert repo-beschrijvingen, PR-titels, branchnamen, bestandsnamen
en de PR-URL. Die komen van GitHub en **iedereen** kan ze zetten door een PR te
openen op een publieke repo. Tot 2026-09-07 gingen ze via `innerHTML`; gemeten met
een nagebootste payload voerde dat script uit in de PWA — waar het apparaat-token
in `localStorage` staat — en werd `javascript:…` een klikbare link.

De test voert de payload op de werkkopie uit en controleert vier dingen: het script
draait niet, er komt geen element uit de payload in de DOM, een `javascript:`-URL
wordt geen klikbare href, en de titel is nog steeds **leesbaar als tekst** — een
fix die de weergave sloopt is ook fout.

Bij het vinden draaide dezelfde payload één keer tegen het toen kwetsbare `main`,
ter bewijs dat het geen theorie was:

| | main (toen) | gepatcht |
|---|---|---|
| script uitgevoerd | ja | nee |
| geïnjecteerde `<img>` | 4 | 0 |
| link-href | `javascript:window.__XSS=1` | `https://github.com/` |

Die controle-run zit niet meer in het script: nu de fix in main staat, zou hij
altijd slagen en dus niets meer meten.

## Waarom `deeplink.js` bestaat

De push-melding wist het kanaal wel (de titel is `#kanaal · auteur`) maar gooide
het weg in de link: `--url "/"`. Elke melding landde dus op de app-root, en dat is
het eerste kanaal. Het kanaal zit nu in de **hash** — die gaat niet naar de server
en geeft dus geen tweede cache-entry in de service worker.

De test dekt de vier gevallen die uit elkaar lopen: verse start met hash, een al
open venster dat een hash-wijziging krijgt (geen herlaad, dus `hashchange`),
handmatig wisselen dat de hash meeschrijft, en een onbekende hash — die laat een
open venster staan maar valt bij een verse start terug op het eerste kanaal.

## Wat ze NIET dekken

- Schrijfpaden door de web-app zelf: die vragen het apparaat-token en dat hoort
  niet in een test te staan. De 401-gate wordt wel getest, de kant erachter via
  `chat/test_admin_key.py` en een handmatige smoke.
- Web Push: vraagt een echt toestel en toestemming.

## Waarom `offline-boot.js` bestaat

Omdat de app maandenlang kon hangen op "laden…" zonder dat iets dat merkte.
De service worker serveert bij een koude start (tunnel nog niet op) bewust de
gecachete shell; de app begon dan te draaien zonder netwerk, sneuvelde op zijn
eerste fetch, en zette daardoor nooit de poll-timer die hem had kunnen laten
herstellen. Alle andere e2e-tests draaien tegen een gezonde API en zien dat
dus niet. Deze blokkeert `/api/*`, laat de app starten, deblokkeert, en meet
dat hij zichzelf herstelt — zonder herlaad.

## Waarom `inloggen.js` een verse installatie wil

De setup-link maakt de eigenaar en werkt daarna niet meer — dat is precies wat
hij moet doen. Draai hem dus tegen een testinstallatie, of leeg `auth.db` en
herstart; de server drukt dan een nieuwe link af. `api.sh` heeft dat niet nodig:
die kant bewijst juist wat er zónder sessie gebeurt.
