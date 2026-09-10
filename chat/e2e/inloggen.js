// SPDX-License-Identifier: EUPL-1.2
//
// Inloggen in een echte browser, tegen de echte VM. api.sh bewijst wat een
// vreemde NIET mag; dit bewijst de andere kant: dat een mens erin komt, erin
// blijft, er weer uit kan, en dat er dan niets van hem achterblijft.
//
//   SETUP_TOKEN=<token uit de serveruitvoer> \
//   NODE_PATH=<pad>/node_modules node chat/e2e/inloggen.js
//
// Vraagt een verse installatie: de setup-link werkt één keer. Draai hem tegen
// een testinstallatie, of maak er eentje leeg met een lege auth.db.
const { chromium, devices } = require('playwright');
const EXE=process.env.PW_CHROME
  || '/home/agent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const URL_=process.env.BOOMHUIS_URL || 'https://boomhuis-relay.tail8f7877.ts.net';
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
  // Het hidden-attribuut verliest van elke eigen display-regel; zonder de
  // [hidden]-regel in app.css stonden "Code uit je app" en "Setup-token"
  // gewoon in beeld. Daarom een test op wat er ECHT zichtbaar is, niet op
  // het attribuut.
  await p.goto(URL_+'/login', {waitUntil:'load', timeout:45000});
  await p.waitForTimeout(2000);
  const zichtbaar = await p.evaluate(() =>
    [...document.querySelectorAll('.veld')].filter(v => v.offsetParent !== null)
      .map(v => v.querySelector('span').textContent));
  t('alleen naam en wachtwoord op het inlogscherm',
    JSON.stringify(zichtbaar) === JSON.stringify(['Naam','Wachtwoord']),
    JSON.stringify(zichtbaar));

  console.log('— eerste account via de setup-link');
  await p.goto(URL_+'/login?setup='+SETUP, {waitUntil:'load', timeout:45000});
  await p.waitForTimeout(1500);
  t('setup-scherm', (await p.locator('#titel').textContent()).includes('Eerste account'));
  await p.fill('#naam','testeigenaar'); await p.fill('#wachtwoord', WW);
  await p.click('#knop');
  await p.waitForTimeout(6000);
  t('na setup in de app', !/\/login/.test(p.url()), p.url());
  t('kanalen geladen', (await p.locator('.chan').count())>5);
  t('berichten geladen', (await p.locator('#msgs .row').count())>0);
  t('naam in de lade', /testeigenaar/.test(await p.locator('#wieBenJe').textContent().catch(()=>'')));

  console.log('— sessie overleeft een herlaad');
  await p.reload({waitUntil:'load', timeout:45000});
  await p.waitForTimeout(5000);
  t('nog steeds ingelogd', !/\/login/.test(p.url()) && (await p.locator('.chan').count())>5, p.url());

  console.log('— de setup-link is op');
  const nog = await p.evaluate(async (s) => {
    const r = await fetch('/api/setup', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({token:s, naam:'tweede', wachtwoord:'nog een lang wachtwoord'})});
    return r.status;
  }, SETUP);
  t('tweede setup wordt geweigerd', nog === 403, 'status '+nog);

  console.log('— schrijven zonder sessietoken');
  const zonder = await p.evaluate(async () => {
    const r = await fetch('/api/send', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({channel:'x', content:'y'})});
    return r.status;
  });
  t('POST zonder CSRF-token is 403', zonder === 403, 'status '+zonder);

  console.log('— uitloggen');
  const snapshotsVoor = await p.evaluate(() =>
    Object.keys(localStorage).filter(k=>k.startsWith('bh_snap_')).length);
  t('er stonden momentopnamen', snapshotsVoor > 0, snapshotsVoor);
  await p.evaluate(() => uitloggen(false));
  await p.waitForTimeout(4000);
  t('terug op de inlogpagina', /\/login/.test(p.url()), p.url());
  const snapshotsNa = await p.evaluate(() =>
    Object.keys(localStorage).filter(k=>k.startsWith('bh_snap_')).length);
  t('momentopnamen zijn gewist', snapshotsNa === 0, snapshotsNa);
  const naUit = await p.evaluate(async () => (await fetch('/api/channels')).status);
  t('en de sessie is echt weg', naUit === 401, 'status '+naUit);

  console.log('— opnieuw inloggen');
  await p.fill('#naam','testeigenaar'); await p.fill('#wachtwoord', WW);
  await p.click('#knop'); await p.waitForTimeout(6000);
  t('weer binnen', !/\/login/.test(p.url()) && (await p.locator('.chan').count())>5, p.url());

  console.log('— fout wachtwoord');
  await p.evaluate(() => uitloggen(false)); await p.waitForTimeout(3000);
  await p.fill('#naam','testeigenaar'); await p.fill('#wachtwoord','fout wachtwoord hoor');
  await p.click('#knop'); await p.waitForTimeout(3000);
  t('blijft op de inlogpagina met een melding',
    /\/login/.test(p.url()) && !(await p.locator('#melding').isHidden()),
    await p.locator('#melding').textContent().catch(()=>''));

  await b.close();
  console.log(`\n${ok} ok, ${fail} fail`);
  process.exit(fail?1:0);
})();
