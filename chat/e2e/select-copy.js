// SPDX-License-Identifier: MIT
// Message text is selectable and code parts copy with one tap (issue #245).
// Runs the WORKING COPY of chat/ on a phone profile, with /api/* stubbed: no VM,
// no account, nothing posted. https on a routed origin, so the clipboard API
// sees a secure context, as on the real installation.
//
//   NODE_PATH=~/e2e-tools/node_modules node chat/e2e/select-copy.js
const { chromium, devices } = require('playwright');
const fs = require('fs'), path = require('path');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome';
const DIR = path.join(__dirname, '..');
const ORIGIN = 'https://ratatoskr.test';
const CID = 'c1';
const TOKEN = 'ghp_9f8e7d6c5b4a3210';
const BLOCK = 'ssh jumpy kubectl -n chat rollout restart deploy/chat --context homelab-' + 'x'.repeat(60);
const XSS = '<img src=x onerror="window.__XSS=1">';
const msgs = [
  { id: 'a'.repeat(64), author: 'odin', ts: 1700000000, content: 'Plain words you should be able to select.' },
  { id: 'b'.repeat(64), author: 'odin', ts: 1700000060, content: 'Your token: `' + TOKEN + '` (one hour).' },
  { id: 'c'.repeat(64), author: 'odin', ts: 1700000120, content: 'Run this:\n```bash\n' + BLOCK + '\n```\nthen wait.' },
  { id: 'd'.repeat(64), author: 'odin', ts: 1700000180, content: 'markup stays text: `' + XSS + '`' },
];
const TYPES = { '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html',
  '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml', '.png': 'image/png' };

let ok = 0, fail = 0;
const t = (n, c, x = '') => { if (c) { ok++; console.log('  ok   ' + n); }
  else { fail++; console.log('  FAIL ' + n + ' ' + String(x).slice(0, 160)); } };

async function stub(ctx) {
  await ctx.route(ORIGIN + '/**', (r) => {
    const u = new URL(r.request().url());
    const json = (o) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
    if (u.pathname === '/api/sessie') return json({ name: 'tester', csrf: 'x', owner: false });
    if (u.pathname === '/api/channels') return json([{ name: 'general', id: CID, description: 'hub' }]);
    if (u.pathname === '/api/messages') return json({ messages: msgs });
    if (u.pathname === '/api/overview') return json({ channels: [{ id: CID, count: msgs.length }] });
    if (u.pathname.startsWith('/api/')) return json({});
    const f = u.pathname === '/' ? 'index.html' : u.pathname.slice(1);
    const file = path.join(DIR, f);
    if (!fs.existsSync(file) || f.includes('..')) return r.fulfill({ status: 404, body: '' });
    return r.fulfill({ status: 200, contentType: TYPES[path.extname(f)] || 'application/octet-stream',
      body: fs.readFileSync(file) });
  });
}

(async () => {
  const b = await chromium.launch({ executablePath: EXE });
  try {
    const ctx = await b.newContext({ ...devices['Pixel 7'], serviceWorkers: 'block' });
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: ORIGIN });
    await stub(ctx);
    const p = await ctx.newPage();
    const errors = [];
    p.on('pageerror', (e) => errors.push(e.message));
    await p.goto(ORIGIN + '/#general', { waitUntil: 'load' });
    await p.waitForSelector('.bubble code.inline', { timeout: 15000 });

    // 1. Nothing says "not selectable".
    const sel = await p.evaluate(() => [...document.querySelectorAll('.bubble, .bubble code, .bubble pre')]
      .map((n) => getComputedStyle(n).userSelect || getComputedStyle(n).webkitUserSelect));
    t('computed user-select on bubbles and code is never "none"', sel.length >= 6 && !sel.includes('none'), sel);

    // 2. A programmatic selection over a whole bubble holds and reads back.
    const got = await p.evaluate(() => { const n = document.querySelector('.bubble');
      const r = document.createRange(); r.selectNodeContents(n);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r); return s.toString(); });
    t('a bubble can be selected', got === msgs[0].content, got);
    const tok = await p.evaluate(() => { const n = document.querySelectorAll('.bubble')[1];
      const r = document.createRange(); r.selectNodeContents(n);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r); return s.toString(); });
    t('a selection across a copy button copies no ⧉', !tok.includes('⧉') && tok.includes(TOKEN), tok);

    // 3. A poll with a new message does not wipe an open selection…
    msgs.push({ id: 'e'.repeat(64), author: 'odin', ts: 1700000240, content: 'a new one' });
    await p.waitForTimeout(5500);   // the poll is every 4 s
    const kept = await p.evaluate(() => getSelection().toString());
    t('a poll keeps the selection', kept.includes(TOKEN), kept);
    // …and renders once the selection is gone.
    await p.evaluate(() => getSelection().removeAllRanges());
    await p.waitForTimeout(300);
    const n = await p.evaluate(() => document.querySelectorAll('.bubble').length);
    t('the held messages render after the selection ends', n === msgs.length, n);

    // 4. A long press on a bubble is the platform's: no reply, no focus jump.
    const box = await p.locator('.bubble').first().boundingBox();
    const cdp = await ctx.newCDPSession(p);
    const pt = [{ x: box.x + 20, y: box.y + box.height / 2 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: pt });
    await p.waitForTimeout(900);
    const lp = await p.evaluate(() => ({ bar: !!document.getElementById('replyBar') && !document.getElementById('replyBar').hidden,
      focus: document.activeElement && document.activeElement.id, sel: getSelection().toString() }));
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    t('a long press starts no reply and keeps the focus off the composer',
      !lp.bar && lp.focus !== 'input', JSON.stringify(lp));
    console.log('       (native selection after the long press: ' + JSON.stringify(lp.sel) + ')');

    // 5. The copy buttons.
    await p.evaluate(() => navigator.clipboard.writeText(''));
    await p.locator('.bubble code.inline + .copybtn').first().tap();
    await p.waitForTimeout(200);
    t('inline copy puts the token on the clipboard',
      (await p.evaluate(() => navigator.clipboard.readText())) === TOKEN);
    t('the button confirms with ✓',
      (await p.locator('.bubble code.inline + .copybtn').first().textContent()) === '✓');
    await p.locator('.codeblock .copybtn').first().tap();
    await p.waitForTimeout(200);
    t('block copy puts the command on the clipboard, without the fence or language',
      (await p.evaluate(() => navigator.clipboard.readText())) === BLOCK);

    // 6. Clipboard refused: the code is selected instead, and the toast says why.
    await p.evaluate(() => { navigator.clipboard.writeText = () => Promise.reject(new Error('denied')); });
    await p.locator('.codeblock .copybtn').first().tap();
    await p.waitForTimeout(200);
    const fb = await p.evaluate(() => getSelection().toString());
    t('fallback selects the code', fb === BLOCK, fb);

    // 7. Markup in code stays text, and a long line does not widen the page.
    t('no element from markup in a message', await p.evaluate(() =>
      !window.__XSS && !document.querySelector('#msgs img')));
    const wide = await p.evaluate(() => { const m = document.getElementById('msgs');
      return [m.scrollWidth, m.clientWidth]; });
    t('a long code line scrolls inside its block, not the page', wide[0] <= wide[1], wide);

    // 8. Reply still works, through ↩.
    await p.locator('.replybtn').first().tap();
    t('↩ still starts a reply', await p.evaluate(() => !document.getElementById('replyBar').hidden));
    t('no page errors', errors.length === 0, errors.join(' | '));
  } finally {
    await b.close();
  }
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
