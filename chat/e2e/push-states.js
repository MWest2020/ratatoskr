// Does the app SAY something in every notification-permission state?
//
// Why this exists: on 2026-09-13 Mark turned notifications on and nothing
// happened. The access log showed his phone polling normally while it never once
// asked the server for the VAPID key — because the site permission was "denied",
// and in that state the app rendered no button, no message and made no request.
// A phone that cannot notify is then indistinguishable from a phone with no news.
//
// Real push cannot be tested here: headless Chromium has no Push service. What
// CAN be pinned is the branching, which is where the bug was. So we stub
// `Notification.permission` per run and demand that the header always carries a
// 🔔 that leads somewhere.
//
//   NODE_PATH=<pad>/node_modules RATATOSKR_URL=… NAAM=… WW=… node chat/e2e/push-states.js
const { chromium, devices } = require('playwright');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const URL = (process.env.RATATOSKR_URL || process.env.BOOMHUIS_URL
  || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/, '');
const NAAM = process.env.NAAM || process.env.RATATOSKR_NAAM;
const WW = process.env.WW || process.env.RATATOSKR_WW;

let ok = 0, fail = 0;
const t = (naam, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok   ${naam}`); }
  else { fail++; console.log(`  FAIL ${naam} ${extra}`); }
};

async function inState(b, permission) {
  const ctx = await b.newContext({ ...devices['Galaxy S9+'], ignoreHTTPSErrors: true });
  const p = await ctx.newPage();
  // Stub BEFORE any script runs: app-push.js reads Notification.permission at
  // load time, so overriding it afterwards would test nothing.
  await p.addInitScript((perm) => {
    const fake = function () {};
    fake.permission = perm;
    fake.requestPermission = async () => perm;
    Object.defineProperty(window, 'Notification', { value: fake, configurable: true });
  }, permission);
  await p.goto(URL + '/login', { waitUntil: 'load', timeout: 45000 });
  await p.fill('#name', NAAM); await p.fill('#password', WW);
  await p.click('#submit');
  await p.waitForTimeout(7000);
  return { ctx, p };
}

(async () => {
  if (!NAAM || !WW) {
    console.log('NAAM/WW ontbreken — inloggen kan niet, suite gestopt.');
    process.exit(2);
  }
  const b = await chromium.launch({ executablePath: EXE, args: ['--ignore-certificate-errors'] });

  for (const perm of ['denied', 'default']) {
    console.log(`— permission=${perm}`);
    const { ctx, p } = await inState(b, perm);
    const bell = p.locator('#pushBtn');
    t(`er staat een 🔔 bij permission=${perm}`, await bell.count() === 1);
    if (await bell.count() === 1) {
      // Aanwezig is niet hetzelfde als bereikbaar. Gemeten 2026-09-13: de
      // kopbalk was 580px breed op elk telefoonscherm, dus de 🔔 — die er als
      // LAATSTE bij komt — stond 169px buiten beeld op een 360px-toestel.
      // elementFromPoint zegt dan nog steeds "pushBtn", want dat werkt in de
      // layout-viewport; alleen de breedte van de kopbalk verraadt het.
      const pas = await p.evaluate(() => {
        const h = document.querySelector('header');
        const r = document.querySelector('#pushBtn').getBoundingClientRect();
        return { overflow: h.scrollWidth > h.clientWidth, rechts: r.right, breedte: innerWidth };
      });
      t('de kopbalk loopt niet buiten beeld', !pas.overflow, JSON.stringify(pas));
      t('de 🔔 staat volledig binnen het scherm', pas.rechts <= pas.breedte, JSON.stringify(pas));
      // A title is what a long-press shows; it must not be the empty string.
      t('de 🔔 legt uit waar hij voor is', ((await bell.getAttribute('title')) || '').length > 10);
      await bell.click();
      await p.waitForTimeout(800);
      const toast = await p.evaluate(() => {
        const e = document.querySelector('#toast');
        return { zichtbaar: e && getComputedStyle(e).display !== 'none', tekst: (e || {}).textContent || '' };
      });
      if (perm === 'denied') {
        // requestPermission() resolves to "denied" without prompting once a site
        // is blocked, so the only useful answer is where to unblock it.
        t('geblokkeerd => het scherm zegt hoe je het aanzet', toast.zichtbaar
          && /site settings|allow/i.test(toast.tekst), JSON.stringify(toast));
        // Playwright draait in een gewoon venster, dus de tekst hoort de
        // adresbalk-route te noemen. Wie in de geïnstalleerde app zit heeft
        // geen adresbalk en krijgt de Chrome-instellingen-route — dat verschil
        // is de hele reden dat deze tekst twee varianten heeft.
        t('de uitleg noemt de host', /tail|localhost|\./i.test(toast.tekst), toast.tekst);
      } else {
        t('onbeslist => tikken levert een zichtbare reactie', toast.zichtbaar, JSON.stringify(toast));
      }
    }
    await ctx.close();
  }

  // De app draait in Playwright altijd in een gewoon venster, dus display-mode
  // is nooit standalone. Op telefoonformaat hoort hij dat te zeggen: dat is
  // precies het geval dat een halve middag kostte (TWA die terugviel op een
  // Custom Tab, en van buiten niet te onderscheiden van de echte app).
  console.log('— draait-in-een-tab');
  {
    const { ctx, p } = await inState(b, 'granted');
    await p.waitForTimeout(4000);
    const toast = await p.evaluate(() => {
      const e = document.querySelector('#toast');
      return { zichtbaar: e && getComputedStyle(e).display !== 'none', tekst: (e || {}).textContent || '' };
    });
    t('zegt dat je niet in de geïnstalleerde app zit', toast.zichtbaar
      && /browservenster|App installeren/i.test(toast.tekst), JSON.stringify(toast));
    await ctx.close();
  }

  console.log(`\n${ok} ok, ${fail} fail`);
  await b.close();
  process.exit(fail === 0 ? 0 : 1);
})();
