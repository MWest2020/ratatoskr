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

async function loadChannels(){
  channels = await (await fetch("/api/channels")).json();
  const wrap = $("#chanList"); wrap.innerHTML="";
  for(const c of channels){
    const row=document.createElement("div");
    row.className="chan"+(current&&c.id===current.id?" active":"");
    row.dataset.id=c.id;
    row.innerHTML=`<span class="hash">#</span><span class="cn"></span><span class="unread" hidden></span>`;
    row.querySelector(".cn").textContent=c.name;  // textContent: geen HTML-injectie via kanaalnaam
    const open=()=>{ selectChannel(c); closeDrawer(); };
    row.querySelector(".cn").onclick=open;
    row.querySelector(".hash").onclick=open;
    row.querySelector(".unread").onclick=open;
    if(c.name!=="general"){
      const del=document.createElement("button");
      del.className="del"; del.textContent="🗑"; del.title="verwijder #"+c.name;
      del.onclick=async(e)=>{ e.stopPropagation();
        if(!confirm("Kanaal #"+c.name+" verwijderen?")) return;
        const r=await fetch("/api/channels/delete",{method:"POST",
          headers:{"Content-Type":"application/json"},body:JSON.stringify({channel:c.id})});
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
}
async function createChannel(name){
  const r=await fetch("/api/channels/create",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
  const j=await r.json().catch(()=>({}));
  if(!r.ok||j.error){ toast(j.error||"aanmaken mislukt"); return false; }
  await loadChannels();
  const c=channels.find(x=>x.name===name); if(c) selectChannel(c);
  return true;
}
function selectChannel(c){
  current=c; lastCount=0; $("#chanName").textContent=c.name;
  $("#msgs").innerHTML='<div class="empty">laden…</div>';
  loadPinned(c.name);
  refresh(true);
}
async function loadPinned(name){
  const el=$("#pinned");
  let content="";
  try{ const d=await (await fetch("/api/pinned?channel="+encodeURIComponent(name))).json();
    content=(d.content||"").trim(); }catch(e){ content=""; }
  if(!content){ el.hidden=true; el.innerHTML=""; return; }
  const lines=content.split("\n");
  let title="Vastgezette context", body=content;
  if(lines[0] && lines[0].startsWith("#")){
    title=lines[0].replace(/^#+\s*/,"").replace(/^📌\s*/,"");
    body=lines.slice(1).join("\n").replace(/^>.*$/gm,"").trim();
  }
  el.hidden=false; el.classList.add("collapsed");
  el.innerHTML='<div class="head"><span class="pin">📌</span><span class="ttl"></span>'+
    '<span class="caret">▸</span></div><div class="body"></div>';
  el.querySelector(".ttl").textContent=title;
  el.querySelector(".body").textContent=body;
  el.querySelector(".head").onclick=()=>{ el.classList.toggle("collapsed");
    el.querySelector(".caret").textContent=el.classList.contains("collapsed")?"▸":"▾"; };
}
const fmtTime = ts => { const d=new Date(ts*1000);
  return d.toLocaleString("nl-NL",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"}); };

async function refresh(force){
  if(!current) return;
  let data;
  try{ data = await (await fetch("/api/messages?channel="+current.id)).json(); }
  catch(e){ return; }
  if(data.error){ return; }
  const box=$("#msgs");
  const near = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
  const msgs=data.messages||[];
  if(!force && msgs.length===lastCount) return;
  lastCount=msgs.length;
  if(current){ markSeen(current.id, msgs.length); renderBadges(); }
  if(msgs.length===0){ box.innerHTML='<div class="empty">Nog geen berichten — begin het gesprek.</div>'; return; }
  box.innerHTML="";
  for(const m of msgs){
    const row=document.createElement("div");
    row.className="row"+(m.mine?" mine":"");
    const cls = m.author==="mark"?"author-mark":(m.author==="orchestrator"?"author-orchestrator":"");
    row.innerHTML=`<div class="meta"><span class="${cls}">${m.author}</span> · ${fmtTime(m.ts)}</div>`+
      `<div class="bubble"></div>`;
    row.querySelector(".bubble").textContent=m.content;
    box.appendChild(row);
  }
  if(force||near) box.scrollTop=box.scrollHeight;
}

async function send(text){
  const r = await fetch("/api/send",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({channel:current.id, content:text})});
  const j = await r.json().catch(()=>({}));
  if(!r.ok||j.error){ toast(j.error||"versturen mislukt"); return false; }
  return true;
}

