// Playwright hoeft niet in deze repo te staan; wijs er met NODE_PATH naar:
//   NODE_PATH=<pad>/node_modules node chat/e2e/xss.js
const { logIn } = require('./login');
const { chromium, devices } = require('playwright');
const fs=require('fs');
const D=require('path').join(__dirname,'..')+'/';   // de werkkopie van chat/
const EXE='/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const PAYLOAD = '<img src=x onerror="window.__XSS=1"><script>window.__XSS=1</script>';
(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--ignore-certificate-errors']});
  let fail = 0;
  for (const [tag, dir] of [['werkkopie', D]]) {
    const ctx=await b.newContext({...devices['iPhone 13'],ignoreHTTPSErrors:true,serviceWorkers:'block'});
    if (dir) for (const f of ['app.js','app-ui.js','app-modal.js','app-repos.js','index.html'])
      await ctx.route('**/'+f, r=>{ try{ r.fulfill({status:200,
        contentType: f.endsWith('.html')?'text/html':'application/javascript',
        body: fs.readFileSync(dir+f,'utf8')}); }catch(e){ r.continue(); } });
    if (dir) await ctx.route('https://boomhuis-relay.tail8f7877.ts.net/', r=>r.fulfill({status:200,
        contentType:'text/html', body: fs.readFileSync(dir+'index.html','utf8')}));
    // vervalste GitHub-payloads met een kwaadaardige titel/branch/bestandsnaam
    await ctx.route(/\/api\/repos/, r=>r.fulfill({status:200,contentType:'application/json',
      body: JSON.stringify({repos:[{name:'x',full_name:'MWest2020/x',private:false,open_issues:1,
        description:PAYLOAD}]})}));
    await ctx.route(/\/api\/prs/, r=>r.fulfill({status:200,contentType:'application/json',
      body: JSON.stringify({prs:[{number:1,title:PAYLOAD,author:PAYLOAD,head:PAYLOAD,base:'main'}]})}));
    await ctx.route(/\/api\/pr\?/, r=>r.fulfill({status:200,contentType:'application/json',
      body: JSON.stringify({number:1,title:PAYLOAD,author:PAYLOAD,head:PAYLOAD,base:'main',
        additions:1,deletions:0,changed_files:1,url:'javascript:window.__XSS=1',
        files:[{status:'modified',filename:PAYLOAD,additions:1,deletions:0}]})}));
    const p=await ctx.newPage();
    p.on('pageerror',e=>console.log('   PAGEERROR:',e.message));
    p.on('console',m=>{if(m.type()==='error')console.log('   console:',m.text().slice(0,120));});
    await logIn(p);
    await p.goto('https://boomhuis-relay.tail8f7877.ts.net/',{waitUntil:'load',timeout:45000});
    await p.waitForTimeout(4000);
    await p.click('#reposBtn'); await p.waitForTimeout(2000);

    await p.evaluate(()=>document.querySelectorAll('.rrow')[0]?.click()); await p.waitForTimeout(2000);

    await p.evaluate(()=>document.querySelectorAll('.rrow')[0]?.click()); await p.waitForTimeout(2000);
    if (!await p.evaluate(()=>!!document.querySelector('.prdet'))) {
      console.log('  FAIL kon niet tot het PR-detail navigeren — test heeft niets gemeten');
      fail++;
    }
    const r = await p.evaluate(()=>({
      xss: !!window.__XSS,
      imgs: document.querySelectorAll('#reposDrawer img').length,
      href: (document.querySelector('.gh')||{}).href || '(geen)',
      titleText: (document.querySelector('.rn')||{}).textContent || '(geen)'}));
    const textOk = /img src=x/.test(String(r.titleText));     // payload zichtbaar ALS TEKST
    if (r.xss)            { fail++; console.log(`  FAIL ${tag}: de payload is UITGEVOERD`); }
    else                    console.log(`  ok   ${tag}: payload niet uitgevoerd`);
    if (r.imgs)           { fail++; console.log(`  FAIL ${tag}: ${r.imgs} element(en) uit de payload gerenderd`); }
    else                    console.log(`  ok   ${tag}: geen elementen uit de payload`);
    if (/^javascript:/.test(String(r.href))) { fail++; console.log(`  FAIL ${tag}: javascript:-href klikbaar`); }
    else                    console.log(`  ok   ${tag}: href = ${String(r.href).slice(0,30)}`);
    if (!textOk)          { fail++; console.log(`  FAIL ${tag}: titel niet leesbaar weergegeven`); }
    else                    console.log(`  ok   ${tag}: titel leesbaar als tekst`);
    await ctx.close();
  }
  await b.close();
  console.log(fail ? `\nmislukt=${fail}` : "\nalle checks geslaagd");
  process.exit(fail ? 1 : 0);
})();
