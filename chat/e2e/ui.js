// Playwright hoeft niet in deze repo te staan; wijs er met NODE_PATH naar:
//   NODE_PATH=<pad>/node_modules node chat/e2e/ui.js
const { chromium, devices } = require('playwright');
const EXE='/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const URL='https://boomhuis-relay.tail8f7877.ts.net/';
let ok=0, fail=0;
const t=(naam,cond,extra='')=>{ if(cond){ok++;console.log(`  ok   ${naam}`);} else {fail++;console.log(`  FAIL ${naam} ${extra}`);} };

(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--ignore-certificate-errors']});
  const ctx=await b.newContext({...devices['iPhone 13'],ignoreHTTPSErrors:true});
  const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  // Een 401 op een schrijfpoging is verwacht (de token-test hieronder); die telt
  // dus niet als JS-fout, anders faalt de suite op haar eigen scenario.
  p.on('console',m=>{ if(m.type()==='error' && !/401/.test(m.text())) errs.push('console: '+m.text()); });
  await p.goto(URL,{waitUntil:'load',timeout:45000});
  await p.waitForTimeout(7000);

  console.log('— shell');
  t('geen JS-fouten bij laden', errs.length===0, errs.slice(0,2).join(' | '));
  t('service worker geregistreerd', await p.evaluate(()=>navigator.serviceWorker.getRegistration().then(r=>!!r)));
  t('kanaallijst gevuld', (await p.locator('.chan').count())>5);
  t('composer zichtbaar en raakbaar', await p.evaluate(()=>{
      const c=document.querySelector('#composer'), r=c.getBoundingClientRect();
      return r.bottom<=visualViewport.height+1 &&
             (document.elementFromPoint(r.x+40,r.y+r.height/2)||{}).id==='input';}));
  t('shell-hoogte volgt visualViewport', await p.evaluate(()=>
      getComputedStyle(document.documentElement).getPropertyValue('--app-h').trim().endsWith('px')));

  console.log('— kanaal wisselen');
  await p.click('#switch'); await p.waitForTimeout(600);
  t('lade opent', await p.evaluate(()=>document.querySelector('#drawer').classList.contains('open')));
  const box=await p.evaluate(()=>{const r=[...document.querySelectorAll('.chan')].find(x=>x.querySelector('.cn')?.textContent==='bouw');
     const rr=r.getBoundingClientRect(), m=r.querySelector('.cmeta').getBoundingClientRect();
     return {right:rr.right,top:rr.top,h:rr.height,metaRight:m.right};});
  await p.mouse.click((box.metaRight+box.right)/2, box.top+box.h/2);   // dode zone van vroeger
  await p.waitForTimeout(2500);
  t('tik naast de naam wisselt van kanaal', await p.evaluate(()=>document.querySelector('#chanName').textContent==='bouw'));
  t('en sluit de lade', await p.evaluate(()=>!document.querySelector('#drawer').classList.contains('open')));

  console.log('— berichten');
  await p.click('#switch'); await p.waitForTimeout(500);
  await p.evaluate(()=>[...document.querySelectorAll('.chan')].find(x=>x.querySelector('.cn')?.textContent==='general').click());
  await p.waitForTimeout(4000);
  const msgs=await p.evaluate(()=>({n:document.querySelectorAll('#msgs > *').length,
     namen:[...document.querySelectorAll('#msgs .meta > span')].slice(-6).map(e=>e.textContent.trim()),
     // markup in een naam of inhoud mag NOOIT een element worden
     geinjecteerd: document.querySelectorAll('#msgs img,#msgs script').length}));
  t('berichten gerenderd', msgs.n>3, JSON.stringify(msgs).slice(0,120));
  t('afzendernamen zichtbaar', msgs.namen.length>0, JSON.stringify(msgs.namen));
  t('geen markup uit berichten gerenderd', msgs.geinjecteerd===0);

  console.log('— agents-lade');
  await p.click('#agentsBtn'); await p.waitForTimeout(2500);
  t('agents-lade opent', await p.evaluate(()=>document.querySelector('#agentsDrawer').classList.contains('open')));
  const ag=await p.evaluate(()=>document.querySelector('#agentList').textContent);
  t('odin staat in de vloot', /odin/i.test(ag), ag.slice(0,100));
  t('coordinator staat er NIET meer in', !/coordinator/i.test(ag));
  await p.click('#tabChannels'); await p.waitForTimeout(2500);
  t('tab "per kanaal" vult', (await p.evaluate(()=>document.querySelector('#channelMembers').textContent.length))>50);
  await p.evaluate(()=>document.querySelector('#agentsDrawer').classList.remove('open'));

  console.log('— repos-lade');
  await p.click('#reposBtn'); await p.waitForTimeout(4000);
  t('repos-lade opent', await p.evaluate(()=>document.querySelector('#reposDrawer').classList.contains('open')));
  t('repo-lijst gevuld', (await p.evaluate(()=>document.querySelector('#repoView').textContent.length))>50);
  await p.click('#reposClose'); await p.waitForTimeout(600);
  t('sluitknop werkt', await p.evaluate(()=>!document.querySelector('#reposDrawer').classList.contains('open')));

  console.log('— schrijven zonder token');
  await p.fill('#input','e2e-test-mag-niet-verzonden-worden');
  await p.click('#send'); await p.waitForTimeout(2500);
  t('401 geeft de token-modal (geen prompt-crash)', (await p.locator('.modal-ov').count())>0);
  await p.evaluate(()=>document.querySelector('.modal-cancel')?.click());
  await p.waitForTimeout(1500);
  t('annuleren laat een leesbare melding zien', await p.evaluate(()=>{
      const t=document.querySelector('#toast'); return !!t && /token/i.test(t.textContent);}),
      await p.evaluate(()=>document.querySelector('#toast')?.textContent||'(leeg)'));

  console.log(`\ngeslaagd=${ok} mislukt=${fail}`);
  if(errs.length) console.log('JS-fouten:', errs.slice(0,4));
  await p.screenshot({path:'e2e.png'});
  await b.close();
  process.exit(fail?1:0);
})();
