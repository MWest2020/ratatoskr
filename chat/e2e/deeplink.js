// SPDX-License-Identifier: MIT
// Notifications link to their channel: /#bouw opens #bouw. Without this every
// notification landed on the app root, and so on the first channel.
// NODE_PATH=<path>/node_modules node chat/e2e/deeplink.js
const { logIn } = require('./login');
const { chromium, devices } = require('playwright');
const fs=require('fs');
const D=require('path').join(__dirname,'..')+'/';   // the working copy of chat/
const EXE='/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
let ok=0,fail=0; const t=(n,c,e='')=>{c?(ok++,console.log('  ok   '+n)):(fail++,console.log('  FAIL '+n+' '+e));};
(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--ignore-certificate-errors']});
  const ctx=await b.newContext({...devices['iPhone 13'],ignoreHTTPSErrors:true,serviceWorkers:'block'});
  for (const f of ['app.js','app-ui.js','app-modal.js','app-repos.js','index.html'])
    await ctx.route('**/'+f, r=>r.fulfill({status:200,
      contentType: f.endsWith('.html')?'text/html':'application/javascript',
      body: fs.readFileSync(D+f,'utf8')}));
  await ctx.route(/tail8f7877\.ts\.net\/(#.*)?$/, r=>r.fulfill({status:200,
      contentType:'text/html', body: fs.readFileSync(D+'index.html','utf8')}));
  const p=await ctx.newPage();
  p.on('pageerror',e=>console.log('  PAGEERROR:',e.message));

  await logIn(p);
  await p.goto('https://boomhuis-relay.tail8f7877.ts.net/#bouw',{waitUntil:'load',timeout:45000});
  await p.waitForTimeout(5000);
  t('melding naar #bouw opent #bouw', await p.evaluate(()=>document.querySelector('#chanName').textContent==='bouw'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  // an already open window sent to another channel
  await p.evaluate(()=>{ location.hash='#review'; });
  await p.waitForTimeout(3000);
  t('hashwijziging in een open venster wisselt mee', await p.evaluate(()=>document.querySelector('#chanName').textContent==='review'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  // switching by hand writes the hash along
  await p.click('#switch'); await p.waitForTimeout(600);
  await p.evaluate(()=>[...document.querySelectorAll('.chan')].find(x=>x.querySelector('.cn')?.textContent==='marketing').click());
  await p.waitForTimeout(2500);
  t('handmatig wisselen zet de hash', await p.evaluate(()=>location.hash==='#marketing'),
    await p.evaluate(()=>location.hash));

  // an unknown hash in an ALREADY OPEN window: do not jump away
  await p.evaluate(()=>{ location.hash='#bestaat-niet'; });
  await p.waitForTimeout(2000);
  t('onbekende hash laat een open venster staan', await p.evaluate(()=>document.querySelector('#chanName').textContent==='marketing'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  // an unknown hash on a FRESH start: fall back on the first channel
  await p.reload({waitUntil:'load'});
  await p.waitForTimeout(5000);
  t('onbekende hash valt bij een verse start terug op het eerste', await p.evaluate(()=>document.querySelector('#chanName').textContent==='general'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  console.log(`\ngeslaagd=${ok} mislukt=${fail}`);
  await b.close(); process.exit(fail?1:0);
})();
