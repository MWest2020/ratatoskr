// Rooktest in een ECHTE browser: doet de app het, of staat hij stil?
//
// Waarom dit bestaat, precies: op 2026-09-11 draaide Marks installatie een halve
// dag met een chat die de relay niet kon bereiken. `api.sh` gaf 38/38 groen (die
// suite draait zonder sessie en raakt de relay-code niet) en de server was
// gezond op elk HTTP-niveau — maar de app stond op "laden…" en crashte op
// `Cannot read properties of undefined (reading 'name')`. Alleen een browser die
// écht inlogt ziet dat.
//
// De vier dingen die het toen zouden hebben gevangen, en die deze test eist:
//   1. geen JS-fout bij het laden,
//   2. de kanaallijst is gevuld,
//   3. #msgs staat niet meer op "laden…",
//   4. de app POLT ook echt (anders leeft hij niet, hij ziet er alleen zo uit).
//
//   NODE_PATH=<pad>/node_modules PW_CHROME=<chrome> \
//   RATATOSKR_URL=https://… NAAM=… WW=… node chat/e2e/rook.js
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

  const fouten = [];
  let apiCalls = 0;
  p.on('pageerror', (e) => fouten.push('PAGEERROR: ' + e.message));
  p.on('console', (m) => {
    // Een 401 hoort bij scenario's die de app zelf afhandelt; de rest telt.
    if (m.type() === 'error' && !/401/.test(m.text())) fouten.push('console: ' + m.text().slice(0, 160));
  });
  p.on('response', (r) => { if (new global.URL(r.url()).pathname.startsWith('/api/')) apiCalls++; });

  console.log('— inloggen');
  await p.goto(BASIS + '/login', { waitUntil: 'load', timeout: 45000 });
  await p.fill('#naam', NAAM);
  await p.fill('#wachtwoord', WW);
  await p.click('#knop');
  await p.waitForTimeout(9000);
  t('in de app (niet terug op /login)', new global.URL(p.url()).pathname === '/', p.url());

  console.log('— doet de app het');
  const st = await p.evaluate(() => ({
    kanalen: document.querySelectorAll('.chan').length,
    msgs: (document.querySelector('#msgs') || {}).textContent.trim().slice(0, 60),
    sw: !!navigator.serviceWorker.controller,
  }));
  t('geen JS-fouten', fouten.length === 0, fouten.slice(0, 3).join(' | '));
  t('kanaallijst gevuld', st.kanalen > 0, `${st.kanalen} kanalen`);
  // "laden…" is exact het beeld van de storing: shell staat, JS is dood.
  t('berichten geladen (niet op "laden…")', !/^laden/.test(st.msgs), JSON.stringify(st.msgs));
  t('service worker actief', st.sw);

  console.log('— leeft de app (polt hij?)');
  const voor = apiCalls;
  await p.waitForTimeout(20000);
  t('api-verzoeken blijven komen', apiCalls > voor, `${apiCalls - voor} in 20s`);

  console.log(`\n${ok} ok, ${fail} fail`);
  await b.close();
  process.exit(fail === 0 ? 0 : 1);
})();
