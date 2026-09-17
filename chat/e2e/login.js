// SPDX-License-Identifier: MIT
// Logging in for the e2e suites that need the app itself. Since
// `inloggen-per-persoon` no app appears without a session, and filling in the
// same form in three scripts is three times the maintenance.
const BASIS = ((process.env.RATATOSKR_URL || process.env.BOOMHUIS_URL) || 'https://boomhuis-relay.tail8f7877.ts.net').replace(/\/+$/,'');

async function logIn(page){
  const name = (process.env.RATATOSKR_NAAM || process.env.BOOMHUIS_NAAM), pw = (process.env.RATATOSKR_WW || process.env.BOOMHUIS_WW);
  if(!name || !pw){
    console.log('BOOMHUIS_NAAM/BOOMHUIS_WW ontbreken — inloggen kan niet.');
    process.exit(2);
  }
  await page.goto(BASIS.replace(/\/$/, '') + '/login', {waitUntil:'load', timeout:45000});
  await page.fill('#name', name);
  await page.fill('#password', pw);
  await page.click('#submit');
  await page.waitForTimeout(5000);
}

module.exports = { logIn, BASIS };
