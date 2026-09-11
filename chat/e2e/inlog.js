// SPDX-License-Identifier: EUPL-1.2
// Inloggen voor de e2e-suites die de app zelf nodig hebben. Sinds
// `inloggen-per-persoon` komt er zonder sessie geen app in beeld, en drie keer
// hetzelfde formulier invullen in drie scripts is drie keer onderhoud.
const BASIS = (process.env.BOOMHUIS_URL || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/,'');

async function logIn(page){
  const naam = process.env.BOOMHUIS_NAAM, ww = process.env.BOOMHUIS_WW;
  if(!naam || !ww){
    console.log('BOOMHUIS_NAAM/BOOMHUIS_WW ontbreken — inloggen kan niet.');
    process.exit(2);
  }
  await page.goto(BASIS.replace(/\/$/, '') + '/login', {waitUntil:'load', timeout:45000});
  await page.fill('#naam', naam);
  await page.fill('#wachtwoord', ww);
  await page.click('#knop');
  await page.waitForTimeout(5000);
}

module.exports = { logIn, BASIS };
