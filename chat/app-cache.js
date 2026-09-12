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
const LAST_CHANNEL = "bh_laatste_kanaal";
const MAX_MESSAGES = 50;   // genoeg om de draad op te pakken, klein genoeg voor localStorage
const MAX_CHANNELS = 12;

/** Bewaar de laatst opgehaalde berichten van één kanaal. */
function saveSnapshot(cid, msgs){
  if(!cid || !Array.isArray(msgs)) return;
  try{
    localStorage.setItem(SNAPSHOT_PREFIX + cid, JSON.stringify({
      ts: Date.now(),
      messages: msgs.slice(-MAX_MESSAGES),
    }));
    pruneSnapshots();
  }catch(e){ /* vol of geweigerd: dan gewoon geen momentopname */ }
}

/** Onthoud welk kanaal open stond, inclusief naam voor de kop. */
function saveLastChannel(c){
  if(!c || !c.id) return;
  try{ localStorage.setItem(LAST_CHANNEL, JSON.stringify({ id: c.id, name: c.name || "" })); }
  catch(e){ /* niets aan te doen */ }
}

function lastChannel(){
  try{ return JSON.parse(localStorage.getItem(LAST_CHANNEL) || "null"); }
  catch(e){ return null; }
}

/** {ts, messages} of null. */
function readSnapshot(cid){
  try{
    const raw = localStorage.getItem(SNAPSHOT_PREFIX + cid);
    if(!raw) return null;
    const snap = JSON.parse(raw);
    return (snap && Array.isArray(snap.messages) && snap.ts) ? snap : null;
  }catch(e){ return null; }
}

/** Houd de nieuwste MAX_CHANNELS over; de rest is ballast. */
function pruneSnapshots(){
  try{
    const names = Object.keys(localStorage).filter(k => k.startsWith(SNAPSHOT_PREFIX));
    if(names.length <= MAX_CHANNELS) return;
    const byTime = names.map(k => {
      let ts = 0;
      try{ ts = (JSON.parse(localStorage.getItem(k)) || {}).ts || 0; }catch(e){ ts = 0; }
      return { k, ts };
    }).sort((a, b) => b.ts - a.ts);
    for(const old of byTime.slice(MAX_CHANNELS)) localStorage.removeItem(old.k);
  }catch(e){ /* niets aan te doen */ }
}

/** Toon de momentopname van dit kanaal. Geeft false als die er niet is. */
function showSnapshot(cid){
  const snap = readSnapshot(cid);
  if(!snap || !snap.messages.length) return false;
  renderMessages(snap.messages, true);

  const box = document.querySelector("#msgs");
  if(!box) return true;
  const bar = document.createElement("div");
  bar.className = "dated";
  const time = new Date(snap.ts).toLocaleString("nl-NL",
    { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  bar.textContent = "offline — laatst bijgewerkt " + time;
  box.insertBefore(bar, box.firstChild);
  return true;
}

/** Toon wat we het laatst wisten, ook als de kanaallijst nog niet geladen is. */
function showLastKnown(){
  const c = (typeof current !== "undefined" && current) ? current : lastChannel();
  if(!c || !showSnapshot(c.id)) return false;
  const head = document.querySelector("#chanName");
  if(head && !head.textContent) head.textContent = c.name || "";
  return true;
}

/** Alles wissen — na een 401, zodat de volgende persoon op dit apparaat niets
    van de vorige leest. Bij een netwerkfout juist NIET aanroepen. */
function clearSnapshots(){
  try{
    for(const k of Object.keys(localStorage)){
      if(k.startsWith(SNAPSHOT_PREFIX) || k === LAST_CHANNEL) localStorage.removeItem(k);
    }
  }catch(e){ /* niets aan te doen */ }
}
