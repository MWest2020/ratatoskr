// SPDX-License-Identifier: EUPL-1.2
//
// Een momentopname per kanaal, zodat er zonder verbinding iets zinnigs op het
// scherm staat. Meldingen komen over het publieke internet binnen (Web Push
// via FCM), de comms-API alleen over het tailnet — dus "melding binnen, app
// leeg" is een normale toestand, geen storing.
//
// Dit is nadrukkelijk GEEN tweede waarheid: de weergave draagt het tijdstip
// waarop de berichten zijn opgehaald, verse data verdringt hem meteen, en er
// wordt niets mee geschreven. De service worker blijft /api/ ongemoeid laten;
// hij weet niet of iets vers is, de app wel.

const SNAPSHOT_PREFIX = "bh_snap_";
// Zonder kanaallijst (die komt van de API) weet de app offline niet welk
// kanaal open stond. Vandaar deze aparte verwijzing.
const LAATSTE_KANAAL = "bh_laatste_kanaal";
const MAX_BERICHTEN = 50;   // genoeg om de draad op te pakken, klein genoeg voor localStorage
const MAX_KANALEN = 12;

/** Bewaar de laatst opgehaalde berichten van één kanaal. */
function bewaarSnapshot(cid, msgs){
  if(!cid || !Array.isArray(msgs)) return;
  try{
    localStorage.setItem(SNAPSHOT_PREFIX + cid, JSON.stringify({
      ts: Date.now(),
      messages: msgs.slice(-MAX_BERICHTEN),
    }));
    snoeiSnapshots();
  }catch(e){ /* vol of geweigerd: dan gewoon geen momentopname */ }
}

/** Onthoud welk kanaal open stond, inclusief naam voor de kop. */
function bewaarLaatsteKanaal(c){
  if(!c || !c.id) return;
  try{ localStorage.setItem(LAATSTE_KANAAL, JSON.stringify({ id: c.id, name: c.name || "" })); }
  catch(e){ /* niets aan te doen */ }
}

function laatsteKanaal(){
  try{ return JSON.parse(localStorage.getItem(LAATSTE_KANAAL) || "null"); }
  catch(e){ return null; }
}

/** {ts, messages} of null. */
function leesSnapshot(cid){
  try{
    const rauw = localStorage.getItem(SNAPSHOT_PREFIX + cid);
    if(!rauw) return null;
    const snap = JSON.parse(rauw);
    return (snap && Array.isArray(snap.messages) && snap.ts) ? snap : null;
  }catch(e){ return null; }
}

/** Houd de nieuwste MAX_KANALEN over; de rest is ballast. */
function snoeiSnapshots(){
  try{
    const namen = Object.keys(localStorage).filter(k => k.startsWith(SNAPSHOT_PREFIX));
    if(namen.length <= MAX_KANALEN) return;
    const opTijd = namen.map(k => {
      let ts = 0;
      try{ ts = (JSON.parse(localStorage.getItem(k)) || {}).ts || 0; }catch(e){ ts = 0; }
      return { k, ts };
    }).sort((a, b) => b.ts - a.ts);
    for(const oud of opTijd.slice(MAX_KANALEN)) localStorage.removeItem(oud.k);
  }catch(e){ /* niets aan te doen */ }
}

/** Toon de momentopname van dit kanaal. Geeft false als die er niet is. */
function toonSnapshot(cid){
  const snap = leesSnapshot(cid);
  if(!snap || !snap.messages.length) return false;
  renderBerichten(snap.messages, true);

  const box = document.querySelector("#msgs");
  if(!box) return true;
  const balk = document.createElement("div");
  balk.className = "gedateerd";
  const tijd = new Date(snap.ts).toLocaleString("nl-NL",
    { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  balk.textContent = "offline — laatst bijgewerkt " + tijd;
  box.insertBefore(balk, box.firstChild);
  return true;
}

/** Toon wat we het laatst wisten, ook als de kanaallijst nog niet geladen is. */
function toonLaatstBekend(){
  const c = (typeof current !== "undefined" && current) ? current : laatsteKanaal();
  if(!c || !toonSnapshot(c.id)) return false;
  const kop = document.querySelector("#chanName");
  if(kop && !kop.textContent) kop.textContent = c.name || "";
  return true;
}
