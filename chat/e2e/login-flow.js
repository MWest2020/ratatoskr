// SPDX-License-Identifier: EUPL-1.2
//
// Logging in in a real browser, against the real VM. api.sh proves what a
// stranger may NOT do; this proves the other side: that a human gets in, stays
// in, can get out again, and that nothing of them is left behind afterwards.
//
//   SETUP_TOKEN=<token from the server output> \
//   NODE_PATH=<path>/node_modules node chat/e2e/login-flow.js
//
// Wants a fresh installation: the setup link works once. Run it against a test
// installation, or make one empty with an empty auth.db.
const { chromium, devices } = require('playwright');
const EXE=process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const URL_=((process.env.RATATOSKR_URL || process.env.BOOMHUIS_URL) || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/,'');
const SETUP=process.env.SETUP_TOKEN;
if(!SETUP){ console.error('SETUP_TOKEN ontbreekt — zie de serveruitvoer bij een verse installatie'); process.exit(2); }
const WW='een tijdelijk testwachtwoord';
let ok=0, fail=0;
const t=(n,c,x='')=>{ if(c){ok++;console.log('  ok   '+n);} else {fail++;console.log('  FAIL '+n+' '+String(x).slice(0,120));} };

(async()=>{
  const b=await chromium.launch({executablePath:EXE,args:['--ignore-certificate-errors']});
  const ctx=await b.newContext({...devices['iPhone 13'],ignoreHTTPSErrors:true});
  const p=await ctx.newPage();

  console.log('— zonder account');
  await p.goto(URL_+'/', {waitUntil:'load', timeout:45000});
  await p.waitForTimeout(4000);
  t('de app stuurt naar inloggen', /\/login/.test(p.url()), p.url());

  console.log('— het formulier toont alleen wat nodig is');
  // The hidden attribute loses against any display rule of our own; without the
  // [hidden] rule in app.css "Code uit je app" and "Setup-token" were simply
  // visible. Hence a test on what is REALLY visible, not on the attribute.
  await p.goto(URL_+'/login', {waitUntil:'load', timeout:45000});
  await p.waitForTimeout(2000);
  const visible = await p.evaluate(() =>
    [...document.querySelectorAll('.field')].filter(v => v.offsetParent !== null)
      .map(v => v.querySelector('span').textContent));
  t('alleen naam en wachtwoord op het inlogscherm',
    JSON.stringify(visible) === JSON.stringify(['Name','Password']),
    JSON.stringify(visible));

  console.log('— eerste account via de setup-link');
  await p.goto(URL_+'/login?setup='+SETUP, {waitUntil:'load', timeout:45000});
  await p.waitForTimeout(1500);
  t('setup-scherm', (await p.locator('#title').textContent()).includes('First account'));
  await p.fill('#name','testeigenaar'); await p.fill('#password', WW);
  await p.click('#submit');
  await p.waitForTimeout(6000);
  t('na setup in de app', !/\/login/.test(p.url()), p.url());
  t('kanalen geladen', (await p.locator('.chan').count())>5);
  t('berichten geladen', (await p.locator('#msgs .row').count())>0);
  t('naam in de lade', /testeigenaar/.test(await p.locator('#whoAmI').textContent().catch(()=>'')));

  console.log('— sessie overleeft een herlaad');
  await p.reload({waitUntil:'load', timeout:45000});
  await p.waitForTimeout(5000);
  t('nog steeds ingelogd', !/\/login/.test(p.url()) && (await p.locator('.chan').count())>5, p.url());

  console.log('— de setup-link is op');
  const again = await p.evaluate(async (s) => {
    const r = await fetch('/api/setup', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({token:s, naam:'tweede', wachtwoord:'nog een lang wachtwoord'})});
    return r.status;
  }, SETUP);
  t('tweede setup wordt geweigerd', again === 403, 'status '+again);

  console.log('— schrijven zonder sessietoken');
  const without = await p.evaluate(async () => {
    const r = await fetch('/api/send', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({channel:'x', content:'y'})});
    return r.status;
  });
  t('POST zonder CSRF-token is 403', without === 403, 'status '+without);

  console.log('— uitloggen');
  const snapshotsBefore = await p.evaluate(() =>
    Object.keys(localStorage).filter(k=>k.startsWith('bh_snap_')).length);
  t('er stonden momentopnamen', snapshotsBefore > 0, snapshotsBefore);
  await p.evaluate(() => logOut(false));
  await p.waitForTimeout(4000);
  t('terug op de inlogpagina', /\/login/.test(p.url()), p.url());
  const snapshotsAfter = await p.evaluate(() =>
    Object.keys(localStorage).filter(k=>k.startsWith('bh_snap_')).length);
  t('momentopnamen zijn gewist', snapshotsAfter === 0, snapshotsAfter);
  const afterOut = await p.evaluate(async () => (await fetch('/api/channels')).status);
  t('en de sessie is echt weg', afterOut === 401, 'status '+afterOut);

  console.log('— opnieuw inloggen');
  await p.fill('#name','testeigenaar'); await p.fill('#password', WW);
  await p.click('#submit'); await p.waitForTimeout(6000);
  t('weer binnen', !/\/login/.test(p.url()) && (await p.locator('.chan').count())>5, p.url());

  console.log('— fout wachtwoord');
  await p.evaluate(() => logOut(false)); await p.waitForTimeout(3000);
  await p.fill('#name','testeigenaar'); await p.fill('#password','fout wachtwoord hoor');
  await p.click('#submit'); await p.waitForTimeout(3000);
  t('blijft op de inlogpagina met een melding',
    /\/login/.test(p.url()) && !(await p.locator('#message').isHidden()),
    await p.locator('#message').textContent().catch(()=>''));

  await b.close();
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail?1:0);
})();
