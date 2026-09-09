// SPDX-License-Identifier: EUPL-1.2
//
// Alles rond "we kunnen het boomhuis niet bereiken": wat er misging, en de
// twee dingen die de gebruiker eraan kan doen. Los bestand omdat app.js en
// app-ui.js allebei tegen de 200-regelgrens uit CLAUDE.md aan zitten.
//
// Waarom een knop en geen automatisme: een app die zichzelf bij elke storing
// wist, wist ook je ongelezen-status bij een tunnel die twee seconden hikt.

let laatsteFout = "";

// Onthoud waaróp het misging; de melding hieronder toont het.
function noteerVerbindingsfout(e){
  laatsteFout = (e && e.message) ? e.message : (e ? String(e) : "");
}

// Meld dat er geen verbinding is — mét het adres en de fout, want "geen
// verbinding" maakt geen verschil zichtbaar tussen een tunnel die nog niet op
// is en een app die naar een adres wijst dat niet meer bestaat.
// Al gerenderde berichten blijven staan: die zijn nog waar.
function meldGeenVerbinding(){
  const box = document.querySelector("#msgs");
  if(!box || box.querySelector(".row")) return;

  // Is er een momentopname van dit kanaal, toon die dan met zijn datum: bijna
  // altijd nuttiger dan een leeg scherm, en de knoppen komen eronder.
  const metSnapshot = (typeof toonLaatstBekend === "function" && toonLaatstBekend());
  if(!metSnapshot) box.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "empty";

  const kop = document.createElement("div");
  // Het boomhuis staat alleen op het tailnet. Verreweg de vaakste oorzaak
  // van "geen verbinding" is dat Tailscale op het toestel uit staat — dus
  // die staat in de melding zelf, niet in iemands hoofd.
  kop.textContent = metSnapshot
    ? "geen verbinding — staat Tailscale aan?"
    : "geen verbinding met het boomhuis — staat Tailscale aan?";
  wrap.appendChild(kop);

  const waar = document.createElement("div");
  waar.className = "agenthint";
  waar.textContent = location.origin + (laatsteFout ? " — " + laatsteFout : "");
  wrap.appendChild(waar);

  const knoppen = document.createElement("div");
  knoppen.className = "verbindknoppen";

  const nu = document.createElement("button");
  nu.type = "button"; nu.textContent = "opnieuw proberen";
  nu.onclick = () => { if(typeof laadWatErIs === "function") laadWatErIs(); };
  knoppen.appendChild(nu);

  const vers = document.createElement("button");
  vers.type = "button"; vers.textContent = "app verversen";
  vers.title = "meldt de service worker af, wist de cache en herlaadt";
  vers.onclick = () => { vers.disabled = true; vers.textContent = "verversen…"; verversApp(); };
  knoppen.appendChild(vers);

  wrap.appendChild(knoppen);
  box.appendChild(wrap);   // onder de berichten, niet erboven
}

// De enige handeling die een vastgelopen PWA gegarandeerd loskrijgt zonder
// hem te verwijderen en opnieuw te installeren. Faalt een stap, ga door:
// herladen is altijd beter dan blijven staan.
async function verversApp(){
  try{
    if("serviceWorker" in navigator){
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map(r => r.unregister().catch(() => {})));
    }
  }catch(e){ /* niets aan te doen; hieronder toch herladen */ }
  try{
    if(window.caches){
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k).catch(() => {})));
    }
  }catch(e){ /* idem */ }
  // Cache-buster in de URL: een herlaad alleen kan op iOS nog uit de
  // page-cache komen, en dan is er niets veranderd.
  location.replace(location.pathname + "?vers=" + Date.now() + location.hash);
}
