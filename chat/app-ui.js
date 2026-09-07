// SPDX-License-Identifier: EUPL-1.2
async function loadAgents(){
  let data;
  try{ data=await (await fetch("/api/agents")).json(); }catch(e){ return; }
  const wrap=$("#agentList"); wrap.innerHTML="";
  // registry-data via textContent (geen HTML-injectie), zelfde idioom als de per-kanaal-view.
  for(const a of (data.agents||[])){
    const el=document.createElement("div"); el.className="agent";
    const nm=document.createElement("div"); nm.className="nm"; nm.textContent=a.handle; el.appendChild(nm);
    const rol=document.createElement("div"); rol.className="rol"; rol.textContent=a.rol||""; el.appendChild(rol);
    if((a.channels||[]).length){
      const chips=document.createElement("div"); chips.className="chips";
      for(const c of a.channels){
        const ch=document.createElement("span"); ch.className="chip"; ch.textContent=c;
        ch.onclick=()=>{ const cc=channels.find(x=>x.name===c);
          if(cc){ selectChannel(cc); closeAgents(); input.value="@"+a.handle+" "; input.focus(); } };
        chips.appendChild(ch);
      }
      el.appendChild(chips);
    } else { const none=document.createElement("div"); none.className="none"; none.textContent="in geen enkel kanaal"; el.appendChild(none); }
    wrap.appendChild(el);
  }
}
async function loadChannelMembers(){
  const wrap=$("#channelMembers");
  if(wrap.dataset.loaded){ return; }
  wrap.innerHTML='<div class="agenthint">laden…</div>';
  let data; try{ data=await (await fetch("/api/channel-members")).json(); }
  catch(e){ wrap.innerHTML='<div class="agenthint">kon leden niet laden.</div>'; return; }
  wrap.innerHTML="";
  const chans=data.channels||[];
  if(!chans.length){ wrap.innerHTML='<div class="agenthint">geen kanalen (relay onbereikbaar?).</div>'; return; }
  wrap.dataset.loaded="1";
  // Eigen classes (krow/kname/kmem): NIET .agent/.nm/.chip, die dragen ::before-@/#
  // die #netnl tot "@#netnl" zouden maken. DOM + textContent = geen HTML-injectie.
  for(const c of chans){
    const el=document.createElement("div"); el.className="krow";
    const nm=document.createElement("div"); nm.className="kname"; nm.textContent="#"+c.channel; el.appendChild(nm);
    const mem=c.members||[];
    if(mem.length){
      const chips=document.createElement("div"); chips.className="kchips";
      for(const m of mem){
        const ch=document.createElement("span"); ch.className="kmem"; ch.textContent=m.name;
        if(m.rol) ch.title=m.rol;                          // ecosysteem-rol (agent/sessie/mens)
        if(m.channel_role && m.channel_role!=="member"){    // rol op dít kanaal
          const r=document.createElement("span"); r.className="mrole"; r.textContent=" "+m.channel_role; ch.appendChild(r);
        }
        ch.onclick=()=>{ const cc=channels.find(x=>x.name===c.channel); if(cc){ selectChannel(cc); closeAgents(); } };
        chips.appendChild(ch);
      }
      el.appendChild(chips);
    } else { const none=document.createElement("div"); none.className="knone"; none.textContent="geen leden"; el.appendChild(none); }
    wrap.appendChild(el);
  }
}
function showAgentTab(which){
  const agents=which==="agents";
  $("#tabAgents").classList.toggle("on",agents);
  $("#tabChannels").classList.toggle("on",!agents);
  $("#agentList").hidden=!agents;
  $("#channelMembers").hidden=agents;
  if(agents) loadAgents(); else loadChannelMembers();
}
function closeAgents(){ $("#agentsDrawer").classList.remove("open"); }
function closeRepos(){ $("#reposDrawer").classList.remove("open"); }

async function sendTo(channelName, text){
  const c = channels.find(x=>x.name===channelName);
  if(!c){ toast("kanaal #"+channelName+" bestaat niet"); return false; }
  // via _postSend zodat óók dit pad de mention-pop-up + 409-afhandeling krijgt
  // (bv. @reviewer die nog geen lid van #review is).
  return await _postSend(text, c.id, false, new Set());
}
// UI-bindings
$("#switch").onclick=()=>$("#drawer").classList.add("open");
$("#agentsBtn").onclick=()=>{ $("#channelMembers").dataset.loaded=""; showAgentTab("agents"); $("#agentsDrawer").classList.add("open"); };
$("#tabAgents").onclick=()=>showAgentTab("agents");
$("#tabChannels").onclick=()=>showAgentTab("channels");
$("#reposBtn").onclick=openRepos;
$("#reposClose").onclick=closeRepos;
$("#reposDrawer").onclick=e=>{ if(e.target.id==="reposDrawer") closeRepos(); };
$("#newChan").addEventListener("submit", async e=>{
  e.preventDefault();
  const inp=$("#newChanName"); const name=(inp.value||"").trim().toLowerCase();
  if(!name) return;
  if(await createChannel(name)){ inp.value=""; closeDrawer(); }
});
$("#agentsDrawer").onclick=e=>{ if(e.target.id==="agentsDrawer") closeAgents(); };
$("#drawer").onclick=e=>{ if(e.target.id==="drawer") closeDrawer(); };
function closeDrawer(){ $("#drawer").classList.remove("open"); }
const input=$("#input");
input.addEventListener("input",()=>{ input.style.height="auto";
  input.style.height=Math.min(input.scrollHeight,120)+"px"; });
$("#composer").addEventListener("submit", async e=>{
  e.preventDefault();
  const t=input.value.trim(); if(!t||!current) return;
  $("#send").disabled=true;
  // try/finally: knop nooit permanent op slot (bv. netwerkfout mid-send).
  try {
    const ok=await send(t);
    if(ok){ input.value=""; input.style.height="auto"; await refresh(true); }
  } finally { $("#send").disabled=false; }
});
input.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); $("#composer").requestSubmit(); }
});

(async function init(){
  await loadChannels();
  selectChannel(channels[0]);
  await loadChannels();
  loadOverview();
  pollTimer=setInterval(()=>refresh(false), 4000);
  setInterval(loadOverview, 12000);
  document.addEventListener("visibilitychange",()=>{ if(!document.hidden){ refresh(false); loadOverview(); } });
})();

// --- PWA: service worker + installeer-knop ---
if("serviceWorker" in navigator){
  navigator.serviceWorker.register("/sw.js").catch(()=>{});
}
let deferredPrompt=null;
window.addEventListener("beforeinstallprompt", e=>{
  e.preventDefault(); deferredPrompt=e;
  const b=document.createElement("button");
  b.textContent="Installeer";
  b.style.cssText="margin-left:.4rem;background:var(--accent);color:#15130f;border:0;border-radius:10px;padding:.4rem .7rem;font-size:.85rem;font-weight:700";
  b.onclick=async()=>{ b.remove(); if(!deferredPrompt)return; deferredPrompt.prompt();
    await deferredPrompt.userChoice; deferredPrompt=null; };
  document.querySelector("header").appendChild(b);
});
// Web Push zit in app-push.js (aparte module, na deze).
