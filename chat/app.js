// SPDX-License-Identifier: EUPL-1.2
const $ = s => document.querySelector(s);
let channels = [], current = null, lastCount = 0, pollTimer = null;

function toast(t){ const e=$("#toast"); e.textContent=t; e.style.display="block";
  setTimeout(()=>e.style.display="none", 2600); }

// --- ongelezen-teller per kanaal (per device via localStorage) ---
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
    if(!chans.length) return;  // lege/gefaalde overview (bv. 502) → niets bijwerken
    overview={};
    const sm=seenMap(); let changed=false;
    for(const c of chans){          // overzicht kan deels zijn (falende kanalen overgeslagen)
      overview[c.id]={count:c.count};
      if(sm[c.id]==null){ sm[c.id]=c.count; changed=true; } // baseline: nog nooit geopend → nu gelezen
    }
    if(changed){ try{ localStorage.setItem("bh_seen", JSON.stringify(sm)); }catch(e){} }
    renderBadges();
  }catch(e){}
}

// Geeft false terug als de kanalen niet te halen zijn (koude start vóór de
// tunnel op is). Niet gooien: de aanroeper hangt de hele app eraan op.
async function loadChannels(){
  let data;
  try{ data = await (await fetch("/api/channels")).json(); }
  catch(e){ noteerVerbindingsfout(e); return false; }
  if(!Array.isArray(data)) return false;
  channels = data;
  const wrap = $("#chanList"); wrap.innerHTML="";
  for(const c of channels){
    const row=document.createElement("div");
    row.className="chan"+(current&&c.id===current.id?" active":"");
    row.dataset.id=c.id;
    row.innerHTML=`<span class="hash">#</span><span class="cmeta"><span class="cn"></span><span class="cdesc"></span></span><span class="unread" hidden></span>`;
    row.querySelector(".cn").textContent=c.name;  // textContent: geen HTML-injectie via kanaalnaam
    const cd=row.querySelector(".cdesc");
    if(c.description) cd.textContent=c.description; else cd.remove();  // beschrijving = waar het kanaal voor is
    // Klikdoel is de HELE rij, niet de losse spans: de rij is volledige breedte
    // met padding, dus alles naast de tekst was dood oppervlak — je tikte een
    // kanaal aan, er gebeurde niets, en de lade bleef over de invoerbalk staan.
    // De verwijderknop hieronder stopt de propagatie en houdt zijn eigen actie.
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
  // prune bh_seen op de AUTHORITATIEVE, niet-lege kanaallijst (niet op het
  // mogelijk-gedeeltelijke overzicht) — zo wist een deel-storing geen leesstatus.
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
  if(current && current.id===c.id) return;      // geen herlaad-lus via hashchange
  current=c; lastCount=0; $("#chanName").textContent=c.name;
  bewaarLaatsteKanaal(c);   // zodat offline bekend is wat er open stond
  // Hash meeschrijven: een herstart van de PWA (iOS bevriest hem op de
  // achtergrond) brengt je terug in het kanaal waar je was, en een melding kan
  // hierheen linken.
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
  let data;
  try{ data = await (await fetch("/api/messages?channel="+current.id)).json(); }
  catch(e){ noteerVerbindingsfout(e); meldGeenVerbinding(); return; }
  if(data.error){ noteerVerbindingsfout(data.error); meldGeenVerbinding(); return; }
  const msgs=data.messages||[];
  if(!force && msgs.length===lastCount) return;
  lastCount=msgs.length;
  if(current){ markSeen(current.id, msgs.length); renderBadges(); }
  bewaarSnapshot(current.id, msgs);   // voor als er straks geen verbinding is
  renderBerichten(msgs, force);
}

// Ook gebruikt door de offline-weergave, die dezelfde berichten toont maar
// met een gedateerde balk erboven.
function renderBerichten(msgs, force){
  const box=$("#msgs");
  const near = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
  if(msgs.length===0){ box.innerHTML='<div class="empty">Nog geen berichten — begin het gesprek.</div>'; return; }
  box.innerHTML="";
  for(const m of msgs){
    const row=document.createElement("div");
    row.className="row"+(m.mine?" mine":"");
    const cls = m.author==="mark"?"author-mark":(m.author==="orchestrator"?"author-orchestrator":"");
    // Afzendernaam via textContent: hij valt terug op "npub:"+8 tekens uit de
    // relay-payload, en die is niet van ons.
    add(row, add(el("div","meta"), el("span",cls,m.author), " · "+fmtTime(m.ts)),
             el("div","bubble", m.content));
    box.appendChild(row);
  }
  if(force||near) box.scrollTop=box.scrollHeight;
}

async function send(text){ return await _postSend(text, current.id, false, new Set()); }

// cid wordt door de hele retry-flow vastgepind (server stuurt 'm mee in de 409),
// zodat een kanaalwissel het bericht niet naar het verkeerde kanaal stuurt.
async function _postSend(text, cid, force, added){
  let r;
  try {
    r = await postJSON("/api/send",{channel:cid, content:text, force:force});
  } catch(e){ toast("netwerkfout — bericht niet verstuurd"); return false; }
  const j = await r.json().catch(()=>({}));
  if(r.ok && !j.error) return true;
  // 401 apart: dat is geen storing maar een ontbrekend apparaat-token, en die
  // verwarring was precies het probleem.
  if(r.status===401){ toast("schrijf-token nodig — voer 'm in om te kunnen posten"); return false; }
  if(j.missing_agent){
    const who=j.missing_agent, tgt=j.channel||cid;
    const tc=(typeof channels!=="undefined")&&channels.find(x=>x.id===tgt);
    const ch=tc?"#"+tc.name:"dit kanaal";  // ook juist als het doelkanaal ≠ open kanaal
    // 409 ná een force = mention echt onhoudbaar → stoppen (geen tweede pop-up, geen loop).
    if(force){ toast("@"+who+" kan hier niet — bericht niet verstuurd"); return false; }
    // Bekende agent, nog niet toegevoegd → toevoegen, dan NORMAAL opnieuw versturen
    // zodat de relay @who naar het verse lid resolvet en 'm ook echt triggert.
    if(j.known && !added.has(who)){
      const ok = await modalConfirm("@"+who+" zit niet in "+ch+".",
        "Toevoegen en je bericht versturen?", "Toevoegen");
      if(!ok) return false;
      if(!await addAgent(who, tgt)) return false;   // addAgent toont zelf de serverfout
      added.add(who);
      return await _postSend(text, tgt, false, added);
    }
    // Geen agent, óf net toegevoegd maar de relay ziet 't nog niet (409 op dezelfde
    // who) → toch als platte tekst versturen (force-anker; @who blijft dan tekst).
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
// modalConfirm + addAgent staan in app-modal.js (houdt app.js ≤200 regels).

