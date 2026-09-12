// SPDX-License-Identifier: EUPL-1.2
const $ = s => document.querySelector(s);
let channels = [], current = null, lastCount = 0, pollTimer = null;

function toast(t){ const e=$("#toast"); e.textContent=t; e.style.display="block";
  setTimeout(()=>e.style.display="none", 2600); }

// --- unread counter per channel (per device, through localStorage) ---
let overview = {}; // id -> {count}
function seenMap(){ try{ return JSON.parse(localStorage.getItem("bh_seen")||"{}"); }catch(e){ return {}; } }
function markSeen(id, count){ const m=seenMap(); m[id]=count;
  try{ localStorage.setItem("bh_seen", JSON.stringify(m)); }catch(e){} }
function unreadFor(id){ const o=overview[id]; if(!o) return 0;
  const s=seenMap()[id]; if(s==null) return 0; return Math.max(0, o.count - s); }
function renderBadges(){
  document.querySelectorAll("#chanList .chan").forEach(row=>{
    const b=row.querySelector(".unread"); if(!b) return;
    const n=(current&&row.dataset.id===current.id)?0:unreadFor(row.dataset.id);
    if(n>0){ b.textContent=n>99?"99+":n; b.hidden=false; }
    else { b.textContent=""; b.hidden=true; }
  });
}
async function loadOverview(){
  try{ const d=await (await fetch("/api/overview")).json();
    const chans=d.channels||[];
    if(!chans.length) return;  // empty or failed overview (e.g. 502) → update nothing
    overview={};
    const sm=seenMap(); let changed=false;
    for(const c of chans){          // the overview may be partial (failing channels skipped)
      overview[c.id]={count:c.count};
      if(sm[c.id]==null){ sm[c.id]=c.count; changed=true; } // baseline: never opened → read now
    }
    if(changed){ try{ localStorage.setItem("bh_seen", JSON.stringify(sm)); }catch(e){} }
    renderBadges();
  }catch(e){}
}

// Returns false when the channels cannot be fetched (a cold start before the
// tunnel is up). Do not throw: the caller hangs the whole app on this.
async function loadChannels(){
  let response, data;
  try{ response = await fetch("/api/channels"); }
  catch(e){ noteConnectionError(e); return false; }
  if(response.status === 401){ loggedOut(); return false; }
  try{ data = await response.json(); }
  catch(e){ noteConnectionError(e); return false; }
  if(!Array.isArray(data)) return false;
  channels = data;
  const wrap = $("#chanList"); wrap.innerHTML="";
  for(const c of channels){
    const row=document.createElement("div");
    row.className="chan"+(current&&c.id===current.id?" active":"");
    row.dataset.id=c.id;
    row.innerHTML=`<span class="hash">#</span><span class="cmeta"><span class="cn"></span><span class="cdesc"></span></span><span class="unread" hidden></span>`;
    row.querySelector(".cn").textContent=c.name;  // textContent: no HTML injection via a channel name
    const cd=row.querySelector(".cdesc");
    if(c.description) cd.textContent=c.description; else cd.remove();  // the description says what the channel is for
    // The click target is the WHOLE row, not the individual spans: the row is
    // full width with padding, so everything next to the text was dead surface —
    // you tapped a channel, nothing happened, and the drawer stayed over the
    // composer. The delete button below stops propagation and keeps its own action.
    row.onclick=()=>{ selectChannel(c); closeDrawer(); };
    if(c.name!=="general"){
      const del=document.createElement("button");
      del.className="del"; del.textContent="🗑"; del.title="verwijder #"+c.name;
      del.onclick=async(e)=>{ e.stopPropagation();
        if(!confirm("Kanaal #"+c.name+" verwijderen?")) return;
        const r=await postJSON("/api/channels/delete",{channel:c.id});
        const j=await r.json().catch(()=>({}));
        if(!r.ok||j.error){ toast(j.error||"verwijderen mislukt"); return; }
        if(current&&current.id===c.id){ current=null; $("#msgs").innerHTML='<div class="empty">kies een kanaal</div>'; }
        await loadChannels();
      };
      row.appendChild(del);
    }
    wrap.appendChild(row);
  }
  // prune bh_seen on the AUTHORITATIVE, non-empty channel list (not on the
  // possibly partial overview) — that way a partial outage wipes no read state.
  if(channels.length){ try{ const sm=seenMap(); const ids=new Set(channels.map(c=>c.id));
    let ch=false; for(const k of Object.keys(sm)){ if(!ids.has(k)){ delete sm[k]; ch=true; } }
    if(ch) localStorage.setItem("bh_seen", JSON.stringify(sm)); }catch(e){} }
  renderBadges();
  return true;
}

async function createChannel(name){
  const r=await postJSON("/api/channels/create",{name});
  const j=await r.json().catch(()=>({}));
  if(!r.ok||j.error){ toast(j.error||"aanmaken mislukt"); return false; }
  if(j.coordinator_added===false) toast("kanaal aangemaakt — coordinator toevoegen mislukte");
  await loadChannels();
  const c=channels.find(x=>x.name===name); if(c) selectChannel(c);
  return true;
}

function selectChannel(c){
  if(current && current.id===c.id) return;      // no reload loop through hashchange
  current=c; lastCount=0; $("#chanName").textContent=c.name;
  saveLastChannel(c);       // so offline knows what was open
  // Write the hash along: a restart of the PWA (iOS freezes it in the
  // background) brings you back to the channel you were in, and a notification
  // can link here.
  if(decodeURIComponent(location.hash.slice(1))!==c.name)
    history.replaceState(null,"","#"+encodeURIComponent(c.name));
  $("#msgs").innerHTML='<div class="empty">laden…</div>';
  loadPinned(c.name);
  refresh(true);
}
const fmtTime = ts => { const d=new Date(ts*1000);
  return d.toLocaleString("nl-NL",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"}); };

async function refresh(force){
  if(!current) return;
  let response, data;
  try{ response = await fetch("/api/messages?channel="+current.id); }
  catch(e){ noteConnectionError(e); showNoConnection(); return; }
  // A 401 is not a connection problem but a logout: go to the login page, and
  // what is stored locally is cleared.
  if(response.status === 401){ loggedOut(); return; }
  try{ data = await response.json(); }
  catch(e){ noteConnectionError(e); showNoConnection(); return; }
  if(data.error){ noteConnectionError(data.error); showNoConnection(); return; }
  const msgs=data.messages||[];
  if(!force && msgs.length===lastCount) return;
  lastCount=msgs.length;
  if(current){ markSeen(current.id, msgs.length); renderBadges(); }
  saveSnapshot(current.id, msgs);     // for when there is no connection later
  renderMessages(msgs, force);
}

// Also used by the offline view, which shows the same messages but with a dated
// bar above them.
function renderMessages(msgs, force){
  const box=$("#msgs");
  const near = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
  if(msgs.length===0){ box.innerHTML='<div class="empty">Nog geen berichten — begin het gesprek.</div>'; return; }
  box.innerHTML="";
  for(const m of msgs){
    const row=document.createElement("div");
    row.className="row"+(m.mine?" mine":"");
    const cls = m.author==="mark"?"author-mark":(m.author==="orchestrator"?"author-orchestrator":"");
    // Sender name through textContent: it falls back on "npub:" plus 8
    // characters from the relay payload, and that is not ours.
    add(row, add(el("div","meta"), el("span",cls,m.author), " · "+fmtTime(m.ts)),
             el("div","bubble", m.content));
    box.appendChild(row);
  }
  if(force||near) box.scrollTop=box.scrollHeight;
}

async function send(text){ return await _postSend(text, current.id, false, new Set()); }

// The cid is pinned through the whole retry flow (the server sends it along in
// the 409), so switching channels does not send the message to the wrong one.
async function _postSend(text, cid, force, added){
  let r;
  try {
    r = await postJSON("/api/send",{channel:cid, content:text, force:force});
  } catch(e){ toast("netwerkfout — bericht niet verstuurd"); return false; }
  const j = await r.json().catch(()=>({}));
  if(r.ok && !j.error) return true;
  // 401 separately: that is not an outage but a missing device token, and that
  // confusion was exactly the problem.
  if(r.status===401){ toast("schrijf-token nodig — voer 'm in om te kunnen posten"); return false; }
  if(j.missing_agent){
    const who=j.missing_agent, tgt=j.channel||cid;
    const tc=(typeof channels!=="undefined")&&channels.find(x=>x.id===tgt);
    const ch=tc?"#"+tc.name:"dit kanaal";  // right even when the target ≠ open channel
    // a 409 AFTER a force = the mention is truly untenable → stop (no second pop-up, no loop).
    if(force){ toast("@"+who+" kan hier niet — bericht niet verstuurd"); return false; }
    // A known agent, not yet added → add it, then send again NORMALLY so the
    // relay resolves @who to the fresh member and really triggers it.
    if(j.known && !added.has(who)){
      const ok = await modalConfirm("@"+who+" zit niet in "+ch+".",
        "Toevoegen en je bericht versturen?", "Toevoegen");
      if(!ok) return false;
      if(!await addAgent(who, tgt)) return false;   // addAgent shows the server error
      added.add(who);
      return await _postSend(text, tgt, false, added);
    }
    // Not an agent, OR just added but the relay does not see it yet (a 409 on the
    // same who) → send as plain text anyway (force anchor; @who then stays text).
    if(j.can_force){
      const just=added.has(who);
      const ok = await modalConfirm(
        "@"+who+(just?" is toegevoegd maar nog niet zichtbaar":" is geen kanaal-lid")+" in "+ch+".",
        just?"Nu toch als platte tekst versturen?":"Toch versturen? De @-tekst blijft dan gewoon tekst.",
        "Versturen");
      if(ok) return await _postSend(text, tgt, true, added);
      return false;
    }
    toast("@"+who+" kan hier niet"); return false;
  }
  toast(j.error||"versturen mislukt"); return false;
}
// modalConfirm and addAgent live in app-modal.js (keeps app.js ≤200 lines).

