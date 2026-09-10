// SPDX-License-Identifier: EUPL-1.2
//
// Koude start zonder tunnel: de service worker serveert de gecachete shell,
// maar de API is onbereikbaar. Vóór `herstel-na-koude-start` sneuvelde
// init() op de eerste fetch, werd de poll-timer nooit gezet en bleef het
// scherm voorgoed op "laden…" staan — ook nadat het netwerk terugkwam.
//
// Deze test blokkeert /api/* bij het laden, meet dat de app het zégt in
// plaats van te blijven laden, deblokkeert, en meet dat hij zich herstelt
// zonder herlaad.
//
//   NODE_PATH=<pad>/node_modules node chat/e2e/offline-boot.js
const { chromium, devices } = require('playwright');
const { logIn } = require('./inlog');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const URL = process.env.BOOMHUIS_URL || 'https://boomhuis-relay.tail8f7877.ts.net/';
let ok = 0, fail = 0;
const t = (naam, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok   ${naam}`); }
  else { fail++; console.log(`  FAIL ${naam} ${extra}`); }
};

// Wacht tot een voorwaarde waar is, of geef op na `ms`.
async function until(page, fn, ms = 15000) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    if (await page.evaluate(fn)) return true;
    await page.waitForTimeout(250);
  }
  return false;
}

(async () => {
  const b = await chromium.launch({ executablePath: EXE, args: ['--ignore-certificate-errors'] });
  const ctx = await b.newContext({ ...devices['iPhone 13'], ignoreHTTPSErrors: true });
  const p = await ctx.newPage();

  // Eerst inloggen — mét netwerk, want zonder sessie is er geen app om offline
  // te krijgen.
  await logIn(p);

  // De storing: alles behalve /api/ mag laden (dat is wat de service worker
  // uit de cache zou serveren); de API is er niet.
  let apiDown = true;
  await ctx.route('**/api/**', (route) => (apiDown ? route.abort('failed') : route.continue()));

  console.log('— koude start zonder API');
  await p.goto(URL, { waitUntil: 'load', timeout: 45000 });
  await p.waitForTimeout(4000);

  const msgsText = () => document.querySelector('#msgs')?.textContent?.trim() || '';
  t('shell is er (composer aanwezig)', await p.evaluate(() => !!document.querySelector('#composer')));
  t('zegt dat er geen verbinding is',
    await until(p, () => {
      const s = document.querySelector('#msgs')?.textContent || '';
      return /verbinding/i.test(s);
    }, 12000),
    await p.evaluate(msgsText));
  t('blijft niet stil op "laden…" staan',
    !/^laden…$/.test(await p.evaluate(msgsText)),
    await p.evaluate(msgsText));
  // De melding moet bruikbaar zijn: welk adres, welke fout, en een uitweg.
  t('melding noemt het adres', (await p.evaluate(msgsText)).includes(await p.evaluate(() => location.origin)),
    await p.evaluate(msgsText));
  t('knop "opnieuw proberen" staat er',
    await p.evaluate(() => [...document.querySelectorAll('#msgs button')]
      .some(b => /opnieuw proberen/i.test(b.textContent))));
  t('knop "app verversen" staat er',
    await p.evaluate(() => [...document.querySelectorAll('#msgs button')]
      .some(b => /app verversen/i.test(b.textContent))));

  console.log('— netwerk komt op');
  apiDown = false;
  t('kanalen komen alsnog binnen, zonder herlaad',
    await until(p, () => document.querySelectorAll('.chan').length > 5, 20000),
    'kanaallijst bleef leeg');
  t('berichten komen alsnog binnen',
    await until(p, () => document.querySelectorAll('#msgs .row').length > 0, 20000),
    await p.evaluate(msgsText));
  t('geen verbindingsmelding meer',
    !/verbinding/i.test(await p.evaluate(msgsText)),
    await p.evaluate(msgsText));

  console.log('— laatst bekende berichten');
  // Nu is er verse data opgehaald (dus een momentopname). Blokkeer de API
  // opnieuw en herlaad: de berichten horen er nog te staan, gedateerd.
  apiDown = true;
  await p.reload({ waitUntil: 'load', timeout: 45000 });
  await p.waitForTimeout(5000);
  t('berichten blijven staan zonder verbinding',
    (await p.evaluate(() => document.querySelectorAll('#msgs .row').length)) > 0,
    await p.evaluate(msgsText));
  t('en ze zijn zichtbaar gedateerd',
    /laatst bijgewerkt/i.test(await p.evaluate(msgsText)),
    await p.evaluate(msgsText));
  t('met de knoppen er nog onder',
    await p.evaluate(() => [...document.querySelectorAll('#msgs button')]
      .some(b => /app verversen/i.test(b.textContent))));

  apiDown = false;
  t('verse berichten verdringen de datering',
    await until(p, () => {
      const s = document.querySelector('#msgs')?.textContent || '';
      return document.querySelectorAll('#msgs .row').length > 0 && !/laatst bijgewerkt/i.test(s);
    }, 20000),
    await p.evaluate(msgsText));

  console.log('— de uitweg');
  // Verversen moet een geregistreerde service worker en gevulde caches echt
  // opruimen; dat is het enige wat een vastgelopen PWA loskrijgt.
  // Een oude cache erbij zetten is de eerlijke test: na het verversen laadt de
  // app opnieuw en registreert hij zijn worker weer (dat hoort), dus tellen
  // zegt niets — of de OUDE troep weg is, wel.
  const voor = await p.evaluate(async () => {
    await caches.open('boomhuis-shell-oud');
    return {
      sw: (await navigator.serviceWorker.getRegistrations()).length,
      oud: (await caches.keys()).includes('boomhuis-shell-oud'),
    };
  });
  t('service worker draaide en er stond een oude cache', voor.sw > 0 && voor.oud,
    JSON.stringify(voor));

  await p.evaluate(() => verversApp());
  await p.waitForTimeout(5000);
  const na = await p.evaluate(async () => ({
    oud: (await caches.keys()).includes('boomhuis-shell-oud'),
    url: location.search,
  }));
  t('verversen wist de oude cache en herlaadt', na.oud === false && /vers=/.test(na.url),
    JSON.stringify(na));
  t('de app werkt na het verversen', await until(p, () =>
    document.querySelectorAll('.chan').length > 5, 15000));

  await b.close();
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
