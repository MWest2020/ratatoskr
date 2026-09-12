// SPDX-License-Identifier: EUPL-1.2
async function loadAgents(){
  let data;
  try{ data=await (await fetch("/api/agents")).json(); }catch(e){ return; }
  const wrap=$("#agentList"); wrap.innerHTML="";
  // registry data through textContent (no HTML injection), same idiom as the per-channel view.
  for(const a of (data.agents||[])){
    const el=document.createElement("div"); el.className="agent";
    const nm=document.createElement("div"); nm.className="nm"; nm.textContent=a.handle; el.appendChild(nm);
    const role=document.createElement("div"); role.className="role"; role.textContent=a.rol||""; el.appendChild(role);
    if((a.channels||[]).length){
      const chips=document.createElement("div"); chips.className="chips";
      for(const c of a.channels){
        const ch=document.createElement("span"); ch.className="chip"; ch.textContent=c;
        ch.onclick=()=>{ const cc=channels.find(x=>x.name===c);
          if(cc){ selectChannel(cc); closeAgents(); input.value="@"+a.handle+" "; input.focus(); } };
        chips.appendChild(ch);
      }
      el.appendChild(chips);
    } else { const none=document.createElement("div"); none.className="none"; none.textContent="in no channel at all"; el.appendChild(none); }
    wrap.appendChild(el);
  }
}
async function loadChannelMembers(){
  const wrap=$("#channelMembers");
  if(wrap.dataset.loaded){ return; }
  wrap.innerHTML='<div class="agenthint">loading…</div>';
  let data; try{ data=await (await fetch("/api/channel-members")).json(); }
  catch(e){ wrap.innerHTML='<div class="agenthint">could not load members.</div>'; return; }
  wrap.innerHTML="";
  const chans=data.channels||[];
  if(!chans.length){ wrap.innerHTML='<div class="agenthint">no channels (relay unreachable?).</div>'; return; }
  wrap.dataset.loaded="1";
  // Own classes (krow/kname/kmem): NOT .agent/.nm/.chip, those carry ::before @/#
  // which would turn #netnl into "@#netnl". DOM + textContent = no HTML injection.
  for(const c of chans){
    const el=document.createElement("div"); el.className="krow";
    const nm=document.createElement("div"); nm.className="kname"; nm.textContent="#"+c.channel; el.appendChild(nm);
    const mem=c.members||[];
    if(mem.length){
      const chips=document.createElement("div"); chips.className="kchips";
      for(const m of mem){
        const ch=document.createElement("span"); ch.className="kmem"; ch.textContent=m.name;
        if(m.rol) ch.title=m.rol;                          // ecosystem role (agent/session/human)
        if(m.channel_role && m.channel_role!=="member"){    // role on THIS channel
          const r=document.createElement("span"); r.className="mrole"; r.textContent=" "+m.channel_role; ch.appendChild(r);
        }
        ch.onclick=()=>{ const cc=channels.find(x=>x.name===c.channel); if(cc){ selectChannel(cc); closeAgents(); } };
        chips.appendChild(ch);
      }
      el.appendChild(chips);
    } else { const none=document.createElement("div"); none.className="knone"; none.textContent="no members"; el.appendChild(none); }
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
  if(!c){ toast("channel #"+channelName+" does not exist"); return false; }
  // through _postSend so this path also gets the mention pop-up and 409 handling
  // (e.g. @reviewer who is not a member of #review yet).
  return await _postSend(text, c.id, false, new Set());
}
// UI bindings
$("#switch").onclick=()=>$("#drawer").classList.add("open");
$("#agentsBtn").onclick=()=>{ $("#channelMembers").dataset.loaded=""; showAgentTab("agents"); $("#agentsDrawer").classList.add("open"); };
$("#tabAgents").onclick=()=>showAgentTab("agents");
$("#tabChannels").onclick=()=>showAgentTab("channels");
$("#boardBtn").onclick=openBoard;
$("#boardClose").onclick=closeBoard;
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
  // try/finally: never leave the button locked (e.g. a network error mid-send).
  try {
    const ok=await send(t);
    if(ok){ input.value=""; input.style.height="auto"; await refresh(true); }
  } finally { $("#send").disabled=false; }
});
input.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); $("#composer").requestSubmit(); }
});

// The pinned context above the channel — presentation, so here and not in
// app.js (which would otherwise stay above the 200 lines from CLAUDE.md).
async function loadPinned(name){
  const el=$("#pinned");
  let content="";
  try{ const d=await (await fetch("/api/pinned?channel="+encodeURIComponent(name))).json();
    content=(d.content||"").trim(); }catch(e){ content=""; }
  if(!content){ el.hidden=true; el.innerHTML=""; return; }
  const lines=content.split("\n");
  let title="Pinned context", body=content;
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

// Channel from the hash (#bouw), e.g. through a push notification. An unknown
// name → the first channel, as before.
function channelFromHash(){
  const name = decodeURIComponent((location.hash || "").slice(1)).toLowerCase();
  return channels.find(c => c.name === name) || null;
}

// Keeps trying until the channels are in. On a phone the tailnet tunnel comes up
// later than the app: the service worker then serves the cached shell and the
// first fetch fails. Without this retry the screen stayed on "loading…" forever
// after that, even once the network was back.
let channelsIn=false, retry=null;
async function loadWhatThereIs(){
  if(!channelsIn){
    if(!await loadChannels()){
      showNoConnection();
      if(!retry) retry=setTimeout(()=>{ retry=null; loadWhatThereIs(); }, 3000);
      return;
    }
    channelsIn=true;
    if(retry){ clearTimeout(retry); retry=null; }
    selectChannel(channelFromHash() || channels[0]);
    await loadChannels();   // again: now with the active marker
  }
  refresh(false);
  loadOverview();
}

(async function init(){
  // First find out who you are. Only a real 401 goes to the login page; if we
  // cannot reach the server the app simply carries on and the offline view does
  // its job.
  const session = await fetchSession();
  if(session === null){ goToLogin(); return; }
  showWhoYouAre(session);

  // Timers and listeners come before the first network call: on a cold start
  // that call failed, took init() with it, and with it the poll that could have
  // let the app recover.
  pollTimer=setInterval(()=>refresh(false), 4000);
  setInterval(loadOverview, 12000);
  document.addEventListener("visibilitychange",()=>{ if(!document.hidden) loadWhatThereIs(); });
  // The moment the tunnel comes up, instead of waiting for the next poll.
  window.addEventListener("online", loadWhatThereIs);
  // An already open window sent to #channel by a notification: a hash change
  // does not reload the page, so react to it here.
  window.addEventListener("hashchange",()=>{ const c=channelFromHash(); if(c) selectChannel(c); });

  loadWhatThereIs();
})();

// --- PWA: service worker plus install button ---
if("serviceWorker" in navigator){
  // updateViaCache "none": never take the sw script itself from the HTTP cache,
  // otherwise a device can keep re-registering an old worker.
  navigator.serviceWorker.register("/sw.js",{updateViaCache:"none"}).catch(()=>{});
}
let deferredPrompt=null;
window.addEventListener("beforeinstallprompt", e=>{
  e.preventDefault(); deferredPrompt=e;
  const b=document.createElement("button");
  b.textContent="Install";
  b.style.cssText="margin-left:.4rem;background:var(--accent);color:#15130f;border:0;border-radius:10px;padding:.4rem .7rem;font-size:.85rem;font-weight:700";
  b.onclick=async()=>{ b.remove(); if(!deferredPrompt)return; deferredPrompt.prompt();
    await deferredPrompt.userChoice; deferredPrompt=null; };
  document.querySelector("header").appendChild(b);
});
// Web Push lives in app-push.js (a separate module, after this one).
