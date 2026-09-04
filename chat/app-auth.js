// SPDX-License-Identifier: EUPL-1.2
// Schrijf-token per apparaat. De server zet het NOOIT in de pagina: wie de
// pagina kan ophalen (elke tailnet-node) zou het dan kunnen lezen, en juist
// daartegen is het bedoeld. Dus: de gebruiker voert het één keer in, het blijft
// in localStorage van dít apparaat, en elke schrijf-fetch loopt hierlangs.
const TOKEN_KEY = "boomhuis.appToken";

function appToken(){ try { return localStorage.getItem(TOKEN_KEY) || ""; } catch(e){ return ""; } }
function setAppToken(t){ try { localStorage.setItem(TOKEN_KEY, t); } catch(e){} }

// POST met token; bij 401 één keer om het token vragen en opnieuw proberen.
async function postJSON(path, body){
  const send = () => fetch(path, {
    method: "POST",
    headers: Object.assign({"Content-Type": "application/json"},
                           appToken() ? {"X-App-Token": appToken()} : {}),
    body: JSON.stringify(body),
  });
  let r = await send();
  if (r.status !== 401) return r;
  const t = prompt("Schrijf-token voor dit apparaat:");
  if (!t) return r;
  setAppToken(t.trim());
  r = await send();
  // Push-registratie faalt stil zolang er geen token was; nu er wel een is,
  // meteen zelfherstellen zodat meldingen niet stiekem uit blijven.
  if (r.ok && typeof ensurePushSubscription === "function") {
    ensurePushSubscription().catch(() => {});
  }
  return r;
}
