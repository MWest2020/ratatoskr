# End-to-end-tests van de web-chat

Draaien tegen de **echte VM**, niet tegen een mock. Ze vervangen de unittests niet;
ze vangen wat unittests per definitie missen: uitrol, service worker, viewport,
en of de laag eronder ook echt aan staat.

    bash chat/e2e/api.sh        # HTTP: routes, auth-gate, body-grens
    node chat/e2e/ui.js         # browser: shell, kanalen, laden, token-modal
    node chat/e2e/xss.js        # regressietest op de GitHub-rendering

`ui.js` en `xss.js` hebben Playwright nodig (`npm i playwright`) en een Chromium.
Zet `executablePath` bovenaan als je browser elders staat.

## Waarom `xss.js` bestaat

De Repos-lade rendert repo-beschrijvingen, PR-titels, branchnamen, bestandsnamen
en de PR-URL. Die komen van GitHub en **iedereen** kan ze zetten door een PR te
openen op een publieke repo. Tot 2026-09-07 gingen ze via `innerHTML`; gemeten met
een nagebootste payload voerde dat script uit in de PWA — waar het apparaat-token
in `localStorage` staat — en werd `javascript:…` een klikbare link.

De test draait de payload twee keer: tegen de werkkopie en tegen `main`. Hij hoort
`XSS uitgevoerd=false` te geven voor de werkkopie. Blijft de controle-run op `true`
staan nadat de fix in main zit, dan meet de test niet meer wat hij denkt te meten.

## Wat ze NIET dekken

- Schrijfpaden door de web-app zelf: die vragen het apparaat-token en dat hoort
  niet in een test te staan. De 401-gate wordt wel getest, de kant erachter via
  `chat/test_admin_key.py` en een handmatige smoke.
- Web Push: vraagt een echt toestel en toestemming.
