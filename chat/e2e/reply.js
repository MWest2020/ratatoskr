// SPDX-License-Identifier: MIT
// E2E for reply-to-message, in a REAL browser against the real installation:
// a person presses ↩ on a message, sends, and the relay stores a thread reply.
//
//   1. the ↩ on a message opens the "replying to" bar with its author,
//   2. after sending, the bar is gone,
//   3. the reply carries `reply_to` = the parent's id (read back from the server,
//      which reads it from the relay's ["e", id, "", "reply"] tag),
//   4. the app shows the reply with a quote of its parent.
//
// It posts two messages in a TEST channel (default #r6-smoke-4692, which the
// listener does not poll, so no agent is triggered).
//
//   NODE_PATH=<path>/node_modules PW_CHROME=<chrome> \
//   RATATOSKR_URL=https://… NAAM=… WW=… [KANAAL=r6-smoke-4692] node chat/e2e/reply.js
const { chromium, devices } = require('playwright');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASIS = (process.env.RATATOSKR_URL || process.env.BOOMHUIS_URL
  || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/, '');
const NAAM = process.env.NAAM, WW = process.env.WW;
const KANAAL = process.env.KANAAL || 'r6-smoke-4692';

let ok = 0, fail = 0;
const t = (naam, cond, extra = '') => {
  if (cond) { ok++; console.log(`  ok   ${naam}`); }
  else { fail++; console.log(`  FAIL ${naam} ${extra}`); }
};

(async () => {
  if (!NAAM || !WW) { console.log('NAAM/WW missing — cannot sign in.'); process.exit(2); }
  const b = await chromium.launch({ executablePath: EXE, args: ['--ignore-certificate-errors'] });
  const ctx = await b.newContext({ ...devices['Galaxy S9+'], ignoreHTTPSErrors: true });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push(String(e)));
  await p.goto(BASIS + '/login', { waitUntil: 'load', timeout: 45000 });
  await p.fill('#name', NAAM);
  await p.fill('#password', WW);
  await p.click('#submit');
  await p.waitForSelector('.chan', { state: 'attached', timeout: 30000 });

  const opened = await p.evaluate((naam) => {
    const row = [...document.querySelectorAll('.chan')]
      .find((r) => (r.querySelector('.cn') || {}).textContent === naam);
    if (row) row.click();
    return !!row;
  }, KANAAL);
  t(`#${KANAAL} is in the channel list`, opened);
  if (!opened) { await b.close(); process.exit(1); }
  await p.waitForFunction(() => !/loading/.test(document.querySelector('#msgs').textContent),
                          null, { timeout: 30000 });

  const stamp = new Date().toISOString().slice(11, 19);
  const parentText = `e2e reply parent ${stamp} (automated, reply-to-message)`;
  const childText = `e2e reply child ${stamp}`;
  await p.fill('#input', parentText);
  await p.press('#input', 'Enter');
  const rowOf = (txt) => p.locator('.row', { has: p.locator('.bubble', { hasText: txt }) });
  await rowOf(parentText).first().waitFor({ timeout: 30000 });

  await rowOf(parentText).first().locator('.replybtn').click();
  const bar = await p.evaluate(() => {
    const el = document.querySelector('#replyBar');
    return el ? { shown: !el.hidden, text: el.textContent } : null;
  });
  t('↩ opens the "replying to" bar', bar && bar.shown && /replying to/.test(bar.text),
    JSON.stringify(bar));

  await p.fill('#input', childText);
  await p.press('#input', 'Enter');
  await rowOf(childText).first().waitFor({ timeout: 30000 });
  const barAfter = await p.evaluate(() => (document.querySelector('#replyBar') || {}).hidden);
  t('the bar is gone after sending', barAfter === true);

  const data = await p.evaluate(async (texts) => {
    const r = await fetch('/api/messages?channel=' + encodeURIComponent(current.id));
    const ms = (await r.json()).messages || [];
    const parent = ms.filter((m) => m.content === texts[0]).pop();
    const child = ms.filter((m) => m.content === texts[1]).pop();
    return { parent: parent && parent.id, replyTo: child && child.reply_to };
  }, [parentText, childText]);
  t('the reply carries the parent id (relay e-tag "reply")',
    data.parent && data.replyTo === data.parent, JSON.stringify(data));

  await p.waitForTimeout(6000);   // let one poll re-render the list with reply_to
  const quote = await rowOf(childText).first().locator('.quote').textContent().catch(() => '');
  t('the reply shows a quote of its parent', quote.includes(parentText.slice(0, 40)), quote);
  t('no JS error', errors.length === 0, errors.join(' | '));

  await b.close();
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
