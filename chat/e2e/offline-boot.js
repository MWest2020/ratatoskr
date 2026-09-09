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

  await b.close();
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
