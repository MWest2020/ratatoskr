# End-to-end-tests van de web-chat

Draaien tegen de **echte VM**, niet tegen een mock. Ze vervangen de unittests niet;
ze vangen wat unittests per definitie missen: uitrol, service worker, viewport,
en of de laag eronder ook echt aan staat.

    NAAM=… WW=… bash chat/e2e/after-deploy.sh    # DE drie lagen, na elke uitrol
    bash chat/e2e/api.sh          # HTTP: wat een vreemde NIET mag
    NAAM=… WW=… bash chat/e2e/connection.sh   # INGELOGD: praat de chat met de relay?
    NAAM=… WW=… node chat/e2e/smoke.js         # BROWSER: doet de app het echt?
    node chat/e2e/login-flow.js     # browser: inloggen, sessie, uitloggen
    node chat/e2e/ui.js           # browser: shell, kanalen, laden, token-modal
    node chat/e2e/xss.js          # regressietest op de GitHub-rendering
    NAAM=… WW=… node chat/e2e/reply.js  # reply to a message: bar, relay e-tag, quote
    node chat/e2e/deeplink.js     # melding -> juiste kanaal
    node chat/e2e/offline-boot.js # koude start zonder tunnel, en herstel
    NAAM=… WW=… node chat/e2e/push-states.js  # zegt de app iets in ELKE meldingsstaat?

`ui.js`, `xss.js`, `deeplink.js`, `offline-boot.js`, `push-states.js` en `login-flow.js` hebben Playwright nodig en een Chromium. Staat Playwright
elders, wijs er dan met `NODE_PATH` naar; `executablePath` bovenaan het script
wijst naar de browser.

    NODE_PATH=~/ergens/node_modules node chat/e2e/ui.js

Op agent-lxc staat die buiten de repo, met de browsers uit de cache ernaast:

    NODE_PATH=/home/agent/e2e-tools/node_modules \
    PW_CHROME=/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome \
    RATATOSKR_URL=https://… NAAM=… WW=… bash chat/e2e/after-deploy.sh

Opnieuw opzetten als die map weg is (de browsers staan er al, dus geen download):

    mkdir -p ~/e2e-tools && cd ~/e2e-tools && npm init -y
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright

Alle drie geven exitcode 0 bij succes, dus ze zijn te ketenen.

`BOOMHUIS_URL` mag mét of zonder slash aan het eind — de scripts strippen 'm.

## Na elke uitrol: `after-deploy.sh`

Drie lagen, in oplopende echtheid — en je hebt ze alle drie nodig:

| laag | ziet | ziet NIET |
|---|---|---|
| `api.sh` | de gate, zonder sessie | alles wat achter inloggen zit, en de relay |
| `connection.sh` | de relay-kant, ingelogd | of de JS in de browser leeft |
| `smoke.js` | wat een mens ziet | — |

Op 2026-09-11 gaf laag 1 een halve dag 38/38 groen terwijl de app stilstond.
Eén laag is geen test van een uitrol.

Je hebt een testaccount nodig. Maak er een met een uitnodiging en gooi 'm daarna
weg — een staand account dat alles kan lezen is een tweede sleutel die je niet
nodig hebt:

    docker compose exec -T chat python3 adminctl.py invite
    # link gebruiken, dan:
    docker compose exec -T chat python3 adminctl.py delete <naam>

Dit draait **niet** in CI: de installatie zit achter een tailnet of een proxy,
en een runner van GitHub komt daar niet. Het is een uitrol-stap, geen push-stap.

## Waarom `connection.sh` bestaat

`api.sh` draait bewust zónder sessie en raakt daardoor geen enkele regel code die
met de relay praat. Op 2026-09-11 draaide Marks installatie een halve dag met een
chat die de relay niet kon bereiken — de container sprak `relay:3000` aan terwijl
de community van die relay op een andere host staat ("404: no community is
configured for this host") — en `api.sh` gaf al die tijd 38/38 groen. De app
stond op "laden…" en crashte op `Cannot read properties of undefined`.

`connection.sh` logt wél in en eist dat de kanaallijst NIET leeg is: een lege
lijst is precies hoe een onbereikbare relay eruitziet. Bewezen dat hij vangt wat
api.sh miste: met de kapotte instelling faalt hij op 2 van 7.

## Waarom `smoke.js` bestaat

Omdat ook `connection.sh` niet ziet wat een mens ziet. De storing van 11
september eindigde in de browser: `PAGEERROR: Cannot read properties of
undefined (reading 'name')`, nul kanalen in de lade, `#msgs` op "laden…". Precies
die drie dingen eist `smoke.js`, plus dat de app blijft pollen — want een app die
er goed uitziet maar niets meer vraagt, is dood.

Bewezen tegen de échte storing: met de kapotte relay-instelling faalt hij op
3 van 6, met dezelfde foutmelding als toen. Met de goede instelling 6 van 6
groen.

## Wat wél en niet tegen een VERSE installatie draait

Gemeten 2026-09-11 tegen een schone VM (change `uitrol-voor-derden`):

- `api.sh` — **draait**, 38/38 groen. Hij test wat een vreemde niet mag, en dat
  hangt niet van inhoud af.
- `login-flow.js` — **draait voor het installatie-deel**: setup-link, eerste
  account, in de app, CSRF, uitloggen, opnieuw inloggen. De assertions die
  kanalen of berichten nodig hebben falen, want een verse relay heeft die niet.
- `ui.js`, `deeplink.js`, `offline-boot.js`, `xss.js` — **draaien niet**: ze zijn
  geschreven tegen Marks installatie (meer dan vijf kanalen, een kanaal dat
  `bouw` heet, een kanaal `general`, GitHub-PR-inhoud). Op een verse installatie
  is dat geen falende test maar een ontbrekende fixture.

Wie deze suites tegen een verse installatie wil draaien, heeft eerst een
gezaaide fixture nodig (kanalen + berichten). Dat is eigen werk, geen bijwerking
van een uitrol-change.

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

## Waarom `login-flow.js` een verse installatie wil

De setup-link maakt de eigenaar en werkt daarna niet meer — dat is precies wat
hij moet doen. Draai hem dus tegen een testinstallatie, of leeg `auth.db` en
herstart; de server drukt dan een nieuwe link af. `api.sh` heeft dat niet nodig:
die kant bewijst juist wat er zónder sessie gebeurt.
