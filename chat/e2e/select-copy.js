// SPDX-License-Identifier: MIT
// Message text is selectable and code parts copy with one tap (issue #245).
// Runs the WORKING COPY of chat/ on a phone profile, with /api/* stubbed: no VM,
// no account, nothing posted. https on a routed origin, so the clipboard API
// sees a secure context, as on the real installation. Takes about a minute:
// one check waits out the 30 s hold.
//
//   NODE_PATH=~/e2e-tools/node_modules node chat/e2e/select-copy.js
const { chromium, devices } = require('playwright');
const fs = require('fs'), path = require('path');
const EXE = process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome';
const DIR = path.join(__dirname, '..');
const ORIGIN = 'https://ratatoskr.test';
const TOKEN = 'ghp_9f8e7d6c5b4a3210';
const BLOCK = 'ssh jumpy kubectl -n chat rollout restart deploy/chat --context homelab-' + 'x'.repeat(60);
const XSS = '<img src=x onerror="window.__XSS=1">';
let seq = 0;
const msg = (content) => ({ id: String(++seq).padStart(64, '0'), author: 'odin', ts: 1700000000 + seq * 60, content });
const store = {
  c1: [msg('Plain words you should be able to select.'), msg('Your token: `' + TOKEN + '` (one hour).'),
    msg('Run this:\n```bash\n' + BLOCK + '\n```\nthen wait.'), msg('markup stays text: `' + XSS + '`'),
    msg('empty fence:\n```\n```\nand ``a ` tick`` in double backticks')],
  c2: [msg('bravo says hi')],
};
let bravoDown = false;
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
    if (u.pathname === '/api/channels') return json([{ name: 'alpha', id: 'c1' }, { name: 'bravo', id: 'c2' }]);
    if (u.pathname === '/api/messages') {
      const c = u.searchParams.get('channel');
      if (c === 'c2' && bravoDown) return r.abort('connectionrefused');
      return json({ messages: store[c] || [] });
    }
    if (u.pathname === '/api/overview')
      return json({ channels: Object.keys(store).map((id) => ({ id, count: store[id].length })) });
    if (u.pathname.startsWith('/api/')) return json({});
    const f = u.pathname === '/' ? 'index.html' : u.pathname.slice(1);
    const file = path.join(DIR, f);
    if (f.includes('..') || !fs.existsSync(file)) return r.fulfill({ status: 404, body: '' });
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
    const select = (i) => p.evaluate((i) => { const n = document.querySelectorAll('.bubble')[i];
      const r = document.createRange(); r.selectNodeContents(n);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r); return s.toString(); }, i);
    const state = () => p.evaluate(() => { const pl = document.getElementById('newPill');
      return { bubbles: document.querySelectorAll('.bubble').length, sel: getSelection().toString(),
        pill: pl && !pl.hidden ? pl.textContent : '', seen: JSON.parse(localStorage.getItem('bh_seen') || '{}').c1,
        text: document.getElementById('msgs').textContent, chan: document.getElementById('chanName').textContent }; });
    await p.goto(ORIGIN + '/#alpha', { waitUntil: 'load' });
    await p.waitForSelector('.bubble code.inline', { timeout: 15000 });

    // 1. Selectable.
    const us = await p.evaluate(() => [...document.querySelectorAll('.bubble, .bubble code, .bubble pre')]
      .map((n) => getComputedStyle(n).userSelect || getComputedStyle(n).webkitUserSelect));
    t('computed user-select on bubbles and code is never "none"', us.length >= 6 && !us.includes('none'), us);
    t('a bubble can be selected', (await select(0)) === store.c1[0].content);
    const tok = await select(1);
    t('a selection across a copy button copies no ⧉', !tok.includes('⧉') && tok.includes(TOKEN), tok);

    // 2. Code parts.
    const last = await p.evaluate(() => { const bs = document.querySelectorAll('.bubble'), b = bs[4];
      return { blockBtns: b.querySelectorAll('.codeblock .copybtn').length, blocks: b.querySelectorAll('.codeblock').length,
        inline: b.querySelector('code.inline')?.textContent, text: b.textContent }; });
    t('an empty fence gets no copy button', last.blocks === 1 && last.blockBtns === 0, JSON.stringify(last));
    t('double backticks: inline code, no stray backtick',
      last.inline === 'a ` tick' && !/``/.test(last.text), JSON.stringify(last));

    // 3. A held poll: pill, nothing counted as seen; a tap shows it.
    const seen0 = (await state()).seen, n0 = store.c1.length;
    store.c1.push(msg('first new one'));
    await select(1); await p.waitForTimeout(5000);   // the poll is every 4 s
    let s = await state();
    t('a poll keeps the selection', s.sel.includes(TOKEN), s.sel);
    t('the pill says what waits', s.pill === '1 new message — tap to show', s.pill);
    t('nothing is counted as seen while held', s.seen === seen0 && seen0 === n0, `${s.seen} vs ${seen0}`);
    t('the held message is not shown', s.bubbles === n0, s.bubbles);
    await p.locator('#newPill').tap(); await p.waitForTimeout(300);
    s = await state();
    t('a tap on the pill shows it, counts it and hides the pill',
      s.bubbles === n0 + 1 && s.seen === n0 + 1 && !s.pill, JSON.stringify({ ...s, text: '' }));

    // 4. A selection that stays open does not freeze the chat: 30 s at most.
    store.c1.push(msg('second new one'));
    await select(0); await p.waitForTimeout(5000);
    t('held again while selecting', (await state()).pill !== '');
    await p.waitForTimeout(32000);   // the hold starts at the poll after the select: up to 4 s late
    s = await state();
    t('after 30 s it shows anyway', s.bubbles === n0 + 2 && !s.pill && s.seen === n0 + 2, JSON.stringify({ ...s, text: '' }));

    // 5. A long press on a bubble is the platform's: no reply, no focus jump.
    await p.evaluate(() => getSelection().removeAllRanges());
    const box = await p.locator('.bubble').first().boundingBox();
    const cdp = await ctx.newCDPSession(p);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: box.x + 20, y: box.y + box.height / 2 }] });
    await p.waitForTimeout(900);
    const lp = await p.evaluate(() => { const r = document.getElementById('replyBar');
      return { bar: !!r && !r.hidden, focus: document.activeElement && document.activeElement.id }; });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    t('a long press starts no reply and keeps the focus off the composer', !lp.bar && lp.focus !== 'input', JSON.stringify(lp));

    // 6. Copy buttons.
    await p.evaluate(() => navigator.clipboard.writeText(''));
    await p.locator('.bubble code.inline + .copybtn').first().tap(); await p.waitForTimeout(200);
    t('inline copy puts the token on the clipboard', (await p.evaluate(() => navigator.clipboard.readText())) === TOKEN);
    t('the button confirms with ✓', (await p.locator('.bubble code.inline + .copybtn').first().textContent()) === '✓');
    await p.locator('.codeblock .copybtn').first().tap(); await p.waitForTimeout(200);
    t('block copy puts the command on the clipboard, without fence or language',
      (await p.evaluate(() => navigator.clipboard.readText())) === BLOCK);
    // Clipboard API refused, execCommand copies: no selection left behind.
    await p.evaluate(() => { navigator.clipboard.writeText = () => Promise.reject(new Error('denied'));
      document.execCommand = () => true; });
    await p.locator('.codeblock .copybtn').first().tap(); await p.waitForTimeout(200);
    t('fallback that copies clears its own selection', (await state()).sel === '');
    // Both refused: the code stays selected for the native menu, and a toast says why.
    await p.evaluate(() => { document.execCommand = () => false; });
    await p.locator('.codeblock .copybtn').first().tap(); await p.waitForTimeout(200);
    t('fallback that cannot copy selects the code', (await state()).sel === BLOCK);
    t('…and says why', /could not copy \(denied\)/.test(await p.locator('#toast').textContent()));
    await p.evaluate(() => getSelection().removeAllRanges());

    // 7. Markup stays text; a long line does not widen the page; ↩ replies.
    t('no element from markup in a message', await p.evaluate(() => !window.__XSS && !document.querySelector('#msgs img')));
    const wide = await p.evaluate(() => { const m = document.getElementById('msgs'); return [m.scrollWidth, m.clientWidth]; });
    t('a long code line scrolls inside its block, not the page', wide[0] <= wide[1], wide);
    await p.locator('.replybtn').first().tap();
    t('↩ still starts a reply', await p.evaluate(() => !document.getElementById('replyBar').hidden));

    // 8. A held list belongs to its channel: held in #alpha, switch to #bravo
    // whose fetch fails, end the selection: alpha's messages must not show.
    store.c1.push(msg('ALPHA-ONLY'));
    await select(0); await p.waitForTimeout(5000);
    t('held in #alpha', (await state()).pill !== '');
    bravoDown = true;
    await p.evaluate(() => { location.hash = '#bravo'; }); await p.waitForTimeout(1000);
    await p.evaluate(() => getSelection().removeAllRanges()); await p.waitForTimeout(500);
    s = await state();
    t('after the switch, alpha\'s held list does not render under #bravo',
      s.chan === 'bravo' && !s.text.includes('ALPHA-ONLY') && !s.pill, JSON.stringify({ chan: s.chan, pill: s.pill, text: s.text.slice(0, 80) }));
    t('no page errors', errors.length === 0, errors.join(' | '));
  } finally {
    await b.close();
  }
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
