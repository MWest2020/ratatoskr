// SPDX-License-Identifier: EUPL-1.2
// Meldingen linken naar hun kanaal: /#bouw opent #bouw. Zonder dit landde elke
// melding op de app-root, dus op het eerste kanaal.
// NODE_PATH=<pad>/node_modules node chat/e2e/deeplink.js
const { logIn } = require('./login');
const { chromium, devices } = require('playwright');
const fs=require('fs');
const D=require('path').join(__dirname,'..')+'/';   // de werkkopie van chat/
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

  // al open venster dat naar een ander kanaal wordt gestuurd
  await p.evaluate(()=>{ location.hash='#review'; });
  await p.waitForTimeout(3000);
  t('hashwijziging in een open venster wisselt mee', await p.evaluate(()=>document.querySelector('#chanName').textContent==='review'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  // handmatig wisselen schrijft de hash mee
  await p.click('#switch'); await p.waitForTimeout(600);
  await p.evaluate(()=>[...document.querySelectorAll('.chan')].find(x=>x.querySelector('.cn')?.textContent==='marketing').click());
  await p.waitForTimeout(2500);
  t('handmatig wisselen zet de hash', await p.evaluate(()=>location.hash==='#marketing'),
    await p.evaluate(()=>location.hash));

  // onbekende hash in een AL OPEN venster: niet wegspringen
  await p.evaluate(()=>{ location.hash='#bestaat-niet'; });
  await p.waitForTimeout(2000);
  t('onbekende hash laat een open venster staan', await p.evaluate(()=>document.querySelector('#chanName').textContent==='marketing'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  // onbekende hash bij een VERSE start: terugval op het eerste kanaal
  await p.reload({waitUntil:'load'});
  await p.waitForTimeout(5000);
  t('onbekende hash valt bij een verse start terug op het eerste', await p.evaluate(()=>document.querySelector('#chanName').textContent==='general'),
    await p.evaluate(()=>document.querySelector('#chanName').textContent));

  console.log(`\ngeslaagd=${ok} mislukt=${fail}`);
  await b.close(); process.exit(fail?1:0);
})();
