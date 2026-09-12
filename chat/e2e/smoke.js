// Smoke test in a REAL browser: does the app work, or does it stand still?
//
// Why this exists, precisely: on 2026-09-11 Mark's installation ran for half a
// day with a chat that could not reach the relay. `api.sh` reported 38/38 green
// (that suite runs without a session and does not touch the relay code) and the
// server was healthy at every HTTP level — but the app sat on "laden…" and
// crashed on `Cannot read properties of undefined (reading 'name')`. Only a
// browser that really logs in sees that.
//
// The four things that would have caught it then, and that this test demands:
//   1. no JS error while loading,
//   2. the channel list is filled,
//   3. #msgs is no longer on "laden…",
//   4. the app really POLLS (otherwise it is not alive, it only looks it).
//
//   NODE_PATH=<path>/node_modules PW_CHROME=<chrome> \
//   RATATOSKR_URL=https://… NAAM=… WW=… node chat/e2e/smoke.js
const { chromium, devices } = require('playwright');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASIS = (process.env.RATATOSKR_URL || process.env.BOOMHUIS_URL
  || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/, '');
const NAAM = process.env.NAAM || process.env.RATATOSKR_NAAM;
const WW = process.env.WW || process.env.RATATOSKR_WW;

let ok = 0, fail = 0;
const t = (naam, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok   ${naam}`); }
  else { fail++; console.log(`  FAIL ${naam} ${extra}`); }
};

(async () => {
  if (!NAAM || !WW) {
    console.log('NAAM/WW ontbreken — inloggen kan niet, suite gestopt.');
    process.exit(2);
  }
  const b = await chromium.launch({ executablePath: EXE, args: ['--ignore-certificate-errors'] });
  const ctx = await b.newContext({ ...devices['Galaxy S9+'], ignoreHTTPSErrors: true });
  const p = await ctx.newPage();

  const errors = [];
  let apiCalls = 0;
  p.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  p.on('console', (m) => {
    // A 401 belongs to scenarios the app handles itself; the rest counts.
    if (m.type() === 'error' && !/401/.test(m.text())) errors.push('console: ' + m.text().slice(0, 160));
  });
  p.on('response', (r) => { if (new global.URL(r.url()).pathname.startsWith('/api/')) apiCalls++; });

  console.log('— inloggen');
  await p.goto(BASIS + '/login', { waitUntil: 'load', timeout: 45000 });
  await p.fill('#name', NAAM);
  await p.fill('#password', WW);
  await p.click('#submit');
  await p.waitForTimeout(9000);
  t('in de app (niet terug op /login)', new global.URL(p.url()).pathname === '/', p.url());

  console.log('— doet de app het');
  const st = await p.evaluate(() => ({
    channels: document.querySelectorAll('.chan').length,
    msgs: (document.querySelector('#msgs') || {}).textContent.trim().slice(0, 60),
    sw: !!navigator.serviceWorker.controller,
  }));
  t('geen JS-fouten', errors.length === 0, errors.slice(0, 3).join(' | '));
  t('kanaallijst gevuld', st.channels > 0, `${st.channels} kanalen`);
  // "loading…" is exactly the picture of the outage: shell up, JS dead.
  t('berichten geladen (niet op "loading…")', !/^loading/.test(st.msgs), JSON.stringify(st.msgs));
  t('service worker actief', st.sw);

  console.log('— het bord');
  await p.click('#boardBtn');
  await p.waitForTimeout(3000);
  const board = await p.evaluate(() => ({
    open: document.querySelector('#boardDrawer').classList.contains('open'),
    columns: document.querySelectorAll('.bcol').length,
    text: (document.querySelector('#boardView') || {}).textContent.slice(0, 80),
  }));
  t('bord opent', board.open);
  // Four columns, even when they are empty: an empty column should be visibly
  // empty, not absent.
  t('vier kolommen', board.columns === 4, `${board.columns} kolommen: ${board.text}`);
  // A board full of cards you cannot click is a picture. The previous version of
  // this check passed on ZERO cards, so an empty board counted as green — which
  // is exactly the failure Mark found while this suite reported 9/9.
  const brd = await p.evaluate(() => {
    const card = (el) => ({
      via: ((el.querySelector('.bvia') || {}).textContent || '').trim(),
      clickable: el.classList.contains('blink'),
    });
    return {
      cards: [...document.querySelectorAll('.bcard')].map(card),
      heads: [...document.querySelectorAll('.bcol')].map((c) => ({
        title: ((c.querySelector('.bcoltitle') || {}).textContent || '').trim(),
        says: parseInt((c.querySelector('.bcount') || {}).textContent || '0', 10),
        shows: c.querySelectorAll('.bcard').length,
      })),
    };
  });
  t('bord is niet leeg', brd.cards.length > 0, `${brd.cards.length} kaarten`);
  t('elke kaart is klikbaar', brd.cards.every((c) => c.clickable),
    `${brd.cards.filter((c) => !c.clickable).length} zonder doel`);
  t('elke kaart zegt hoe hij gebouwd wordt', brd.cards.every((c) => c.via));
  // A header that says 3 while showing 1 card is worse than no header.
  const off = brd.heads.filter((h) => h.says !== h.shows);
  t('kolomtelling klopt met wat er staat', off.length === 0, JSON.stringify(off));
  await p.click('#boardClose');
  await p.waitForTimeout(500);

  console.log('— leeft de app (polt hij?)');
  const before = apiCalls;
  await p.waitForTimeout(20000);
  t('api-verzoeken blijven komen', apiCalls > before, `${apiCalls - before} in 20s`);

  console.log(`\n${ok} ok, ${fail} fail`);
  await b.close();
  process.exit(fail === 0 ? 0 : 1);
})();
