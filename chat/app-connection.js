// SPDX-License-Identifier: EUPL-1.2
//
// Everything around "we cannot reach the boomhuis": what went wrong, and the two
// things the user can do about it. A separate file because app.js and app-ui.js
// both sit against the 200-line limit from CLAUDE.md.
//
// Why a button and not an automatism: an app that wipes itself on every outage
// also wipes your unread state when the tunnel hiccups for two seconds.

let lastError = "";

// Remember WHAT went wrong; the message below shows it.
function noteConnectionError(e){
  lastError = (e && e.message) ? e.message : (e ? String(e) : "");
}

// Report that there is no connection — with the address and the error, because
// "no connection" shows no difference between a tunnel that is not up yet and an
// app pointing at an address that no longer exists.
// Messages already rendered stay put: those are still true.
function showNoConnection(){
  const box = document.querySelector("#msgs");
  if(!box || box.querySelector(".row")) return;

  // If there is a snapshot of this channel, show it with its date: almost always
  // more useful than an empty screen, and the buttons come below it.
  const withSnapshot = (typeof showLastKnown === "function" && showLastKnown());
  if(!withSnapshot) box.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "empty";

  const head = document.createElement("div");
  // The boomhuis is only on the tailnet. By far the most common cause of "no
  // connection" is Tailscale being off on the device — so that is in the message
  // itself, not in someone's head.
  head.textContent = withSnapshot
    ? "geen verbinding — staat Tailscale aan?"
    : "geen verbinding met het boomhuis — staat Tailscale aan?";
  wrap.appendChild(head);

  const where = document.createElement("div");
  where.className = "agenthint";
  where.textContent = location.origin + (lastError ? " — " + lastError : "");
  wrap.appendChild(where);

  const buttons = document.createElement("div");
  buttons.className = "connbtns";

  const again = document.createElement("button");
  again.type = "button"; again.textContent = "opnieuw proberen";
  again.onclick = () => { if(typeof loadWhatThereIs === "function") loadWhatThereIs(); };
  buttons.appendChild(again);

  const refresh = document.createElement("button");
  refresh.type = "button"; refresh.textContent = "app verversen";
  refresh.title = "meldt de service worker af, wist de cache en herlaadt";
  refresh.onclick = () => { refresh.disabled = true; refresh.textContent = "verversen…"; refreshApp(); };
  buttons.appendChild(refresh);

  wrap.appendChild(buttons);
  box.appendChild(wrap);   // below the messages, not above them
}

// The only action that reliably unsticks a jammed PWA without deleting and
// reinstalling it. If a step fails, carry on: reloading is always better than
// staying put.
async function refreshApp(){
  try{
    if("serviceWorker" in navigator){
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map(r => r.unregister().catch(() => {})));
    }
  }catch(e){ /* nothing to be done; we reload below anyway */ }
  try{
    if(window.caches){
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k).catch(() => {})));
    }
  }catch(e){ /* likewise */ }
  // Cache buster in the URL: on iOS a plain reload can still come from the page
  // cache, and then nothing has changed.
  location.replace(location.pathname + "?vers=" + Date.now() + location.hash);
}
