// SPDX-License-Identifier: EUPL-1.2
//
// Cold start without a tunnel: the service worker serves the cached shell, but
// the API is unreachable. Before `herstel-na-koude-start` init() died on the
// first fetch, the poll timer was never set and the screen stayed on "laden…"
// forever — even once the network came back.
//
// This test blocks /api/* while loading, measures that the app SAYS so instead
// of going on loading, unblocks, and measures that it recovers without a reload.
//
//   NODE_PATH=<path>/node_modules node chat/e2e/offline-boot.js
const { chromium, devices } = require('playwright');
const { logIn } = require('./login');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const URL = ((process.env.RATATOSKR_URL || process.env.BOOMHUIS_URL) || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/,'');
let ok = 0, fail = 0;
const t = (naam, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok   ${naam}`); }
  else { fail++; console.log(`  FAIL ${naam} ${extra}`); }
};

// Wait until a condition is true, or give up after `ms`.
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

  // Log in first — WITH network, because without a session there is no app to
  // take offline.
  await logIn(p);

  // The outage: everything but /api/ may load (that is what the service worker
  // would serve from cache); the API is not there.
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
      return /no connection/i.test(s);
    }, 12000),
    await p.evaluate(msgsText));
  t('blijft niet stil op "loading…" staan',
    !/^loading…$/.test(await p.evaluate(msgsText)),
    await p.evaluate(msgsText));
  // The message has to be usable: which address, which error, and a way out.
  t('melding noemt het adres', (await p.evaluate(msgsText)).includes(await p.evaluate(() => location.origin)),
    await p.evaluate(msgsText));
  t('knop "try again" staat er',
    await p.evaluate(() => [...document.querySelectorAll('#msgs button')]
      .some(b => /try again/i.test(b.textContent))));
  t('knop "refresh app" staat er',
    await p.evaluate(() => [...document.querySelectorAll('#msgs button')]
      .some(b => /refresh app/i.test(b.textContent))));

  console.log('— netwerk komt op');
  apiDown = false;
  t('kanalen komen alsnog binnen, zonder herlaad',
    await until(p, () => document.querySelectorAll('.chan').length > 5, 20000),
    'kanaallijst bleef leeg');
  t('berichten komen alsnog binnen',
    await until(p, () => document.querySelectorAll('#msgs .row').length > 0, 20000),
    await p.evaluate(msgsText));
  t('geen verbindingsmelding meer',
    !/no connection/i.test(await p.evaluate(msgsText)),
    await p.evaluate(msgsText));

  console.log('— laatst bekende berichten');
  // Fresh data has now been fetched (so there is a snapshot). Block the API again
  // and reload: the messages should still be there, dated.
  apiDown = true;
  await p.reload({ waitUntil: 'load', timeout: 45000 });
  await p.waitForTimeout(5000);
  t('berichten blijven staan zonder verbinding',
    (await p.evaluate(() => document.querySelectorAll('#msgs .row').length)) > 0,
    await p.evaluate(msgsText));
  t('en ze zijn zichtbaar gedateerd',
    /last updated/i.test(await p.evaluate(msgsText)),
    await p.evaluate(msgsText));
  t('met de knoppen er nog onder',
    await p.evaluate(() => [...document.querySelectorAll('#msgs button')]
      .some(b => /refresh app/i.test(b.textContent))));

  apiDown = false;
  t('verse berichten verdringen de datering',
    await until(p, () => {
      const s = document.querySelector('#msgs')?.textContent || '';
      return document.querySelectorAll('#msgs .row').length > 0 && !/last updated/i.test(s);
    }, 20000),
    await p.evaluate(msgsText));

  console.log('— de uitweg');
  // Refreshing has to really clean up a registered service worker and filled
  // caches; that is the only thing that unsticks a jammed PWA.
  // Adding an old cache is the honest test: after the refresh the app loads again
  // and re-registers its worker (as it should), so counting says nothing — whether
  // the OLD junk is gone does.
  const before = await p.evaluate(async () => {
    await caches.open('boomhuis-shell-oud');
    return {
      sw: (await navigator.serviceWorker.getRegistrations()).length,
      old: (await caches.keys()).includes('boomhuis-shell-oud'),
    };
  });
  t('service worker draaide en er stond een oude cache', before.sw > 0 && before.old,
    JSON.stringify(before));

  await p.evaluate(() => refreshApp());
  await p.waitForTimeout(5000);
  const after = await p.evaluate(async () => ({
    old: (await caches.keys()).includes('boomhuis-shell-oud'),
    url: location.search,
  }));
  t('verversen wist de oude cache en herlaadt', after.old === false && /vers=/.test(after.url),
    JSON.stringify(after));
  t('de app werkt na het verversen', await until(p, () =>
    document.querySelectorAll('.chan').length > 5, 15000));

  await b.close();
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
