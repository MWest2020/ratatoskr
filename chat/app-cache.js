// SPDX-License-Identifier: EUPL-1.2
//
// A snapshot per channel, so there is something sensible on screen without a
// connection. Notifications arrive over the public internet (Web Push through
// FCM), the comms API only over the tailnet — so "notification in, app empty" is
// a normal state, not an outage.
//
// This is emphatically NOT a second source of truth: the view carries the time
// the messages were fetched, fresh data displaces it at once, and nothing is
// written with it. The service worker still leaves /api/ alone; it does not know
// whether something is fresh, the app does.

const SNAPSHOT_PREFIX = "bh_snap_";
// Without a channel list (which comes from the API) the app does not know
// offline which channel was open. Hence this separate pointer.
const LAST_CHANNEL = "bh_laatste_kanaal";
const MAX_MESSAGES = 50;   // enough to pick up the thread, small enough for localStorage
const MAX_CHANNELS = 12;

/** Store the last fetched messages of one channel. */
function saveSnapshot(cid, msgs){
  if(!cid || !Array.isArray(msgs)) return;
  try{
    localStorage.setItem(SNAPSHOT_PREFIX + cid, JSON.stringify({
      ts: Date.now(),
      messages: msgs.slice(-MAX_MESSAGES),
    }));
    pruneSnapshots();
  }catch(e){ /* full or refused: then simply no snapshot */ }
}

/** Remember which channel was open, name included for the heading. */
function saveLastChannel(c){
  if(!c || !c.id) return;
  try{ localStorage.setItem(LAST_CHANNEL, JSON.stringify({ id: c.id, name: c.name || "" })); }
  catch(e){ /* nothing to be done */ }
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

/** Keep the newest MAX_CHANNELS; the rest is ballast. */
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
  }catch(e){ /* nothing to be done */ }
}

/** Show the snapshot of this channel. Returns false when there is none. */
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

/** Show what we last knew, even when the channel list has not loaded yet. */
function showLastKnown(){
  const c = (typeof current !== "undefined" && current) ? current : lastChannel();
  if(!c || !showSnapshot(c.id)) return false;
  const head = document.querySelector("#chanName");
  if(head && !head.textContent) head.textContent = c.name || "";
  return true;
}

/** Clear everything — after a 401, so the next person on this device reads
    nothing of the previous one. Do NOT call this on a network error. */
function clearSnapshots(){
  try{
    for(const k of Object.keys(localStorage)){
      if(k.startsWith(SNAPSHOT_PREFIX) || k === LAST_CHANNEL) localStorage.removeItem(k);
    }
  }catch(e){ /* nothing to be done */ }
}
