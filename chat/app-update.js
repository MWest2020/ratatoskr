// SPDX-License-Identifier: MIT
//
// Een app die nooit herlaadt, krijgt nooit een fix.
//
// Gemeten 2026-09-13. Er gingen die dag vier uitrollen naar de VM en Marks
// telefoon zag er geen één van. Het toegangslog laat zien waarom: zijn toestel
// deed alleen `/api/*`-aanroepen en géén enkel assetverzoek — geen index.html,
// geen app.css, geen app-push.js. De geïnstalleerde app wordt uit de achtergrond
// hervat, niet genavigeerd, en zonder navigatie kijkt de browser niet of er een
// nieuwe `sw.js` is. De service worker doet netjes skipWaiting() en claim(),
// maar er komt nooit een moment waarop hij dat kán doen.
//
// Gevolg: elke reparatie werd onzichtbaar uitgerold, en "werkt het nu?" was niet
// te beantwoorden — voor hem niet en voor mij niet.
//
// Dit bestand maakt van "de app draait al dagen" geen reden meer om oud te zijn.
(function(){
  if(!("serviceWorker" in navigator)) return;

  const MIN_TUSSEN_CHECKS = 5 * 60 * 1000;
  const PERIODIEK = 30 * 60 * 1000;
  let laatsteCheck = 0;
  // Was deze pagina al onder beheer van een worker? Zo niet, dan is de eerste
  // controllerchange gewoon de eerste installatie en is herladen onzin.
  let hadWorker = !!navigator.serviceWorker.controller;
  let bezigMetHerladen = false;

  async function check(){
    const nu = Date.now();
    if(nu - laatsteCheck < MIN_TUSSEN_CHECKS) return;
    laatsteCheck = nu;
    try{
      const reg = await navigator.serviceWorker.getRegistration();
      if(reg) await reg.update();
    }catch(e){ /* offline of geweigerd: de volgende keer weer */ }
  }

  function ietsOnverzondens(){
    const inp = document.querySelector("#input");
    return !!(inp && inp.value && inp.value.trim());
  }

  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if(!hadWorker){ hadWorker = true; return; }
    if(bezigMetHerladen) return;
    // De nieuwe worker serveert nieuwe bestanden, maar de pagina vóór je draait
    // nog de oude JS en CSS. Zonder herladen zie je een half nieuwe app.
    if(ietsOnverzondens()){
      // Niet ongevraagd herladen terwijl er een onverzonden bericht staat: dat
      // is werk van iemand weggooien voor een cosmetische winst.
      if(typeof toast === "function") toast("nieuwe versie klaar — herlaad als je klaar bent", 8000);
      return;
    }
    bezigMetHerladen = true;
    location.reload();
  });

  document.addEventListener("visibilitychange", () => { if(!document.hidden) check(); });
  window.addEventListener("online", check);
  setInterval(check, PERIODIEK);
})();

// Draai je in de geïnstalleerde app, of in een browservenster dat erop lijkt?
//
// Gemeten 2026-09-13. Mark startte "de app" vanaf zijn app-icoon en zag een
// adresbalk. Het was de TWA van de dag ervoor: die vraagt bij elke start om
// /.well-known/assetlinks.json, dat bestand is weg, dus de verificatie faalt en
// Android valt terug op een Custom Tab. Vanaf het startscherm is dat niet te
// zien — het icoon is hetzelfde, de app is dezelfde, alleen staat er een balk
// boven. Het kostte een halve middag om te achterhalen wat de server al die
// tijd in zijn log had staan.
//
// De app weet dit zelf in één regel. Dus zegt hij het.
(function(){
  function inEchteApp(){
    try{
      return window.matchMedia("(display-mode: standalone)").matches
          || window.matchMedia("(display-mode: fullscreen)").matches
          || window.navigator.standalone === true;   // iOS
    }catch(e){ return true; }  // niet te bepalen? dan niet zeuren
  }
  // Alleen op een telefoon-formaat: op een desktop is een tab de normale manier
  // om dit te gebruiken en zou de melding pure ruis zijn.
  function telefoonAchtig(){
    return window.matchMedia("(max-width:560px)").matches;
  }
  window.addEventListener("load", () => {
    if(inEchteApp() || !telefoonAchtig()) return;
    if(typeof toast !== "function") return;
    setTimeout(() => toast(
      "je draait in een browservenster, niet in de geïnstalleerde app — "
      + "Chrome-menu ⋮ → App installeren", 9000), 2500);
  });
})();
