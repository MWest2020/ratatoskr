// SPDX-License-Identifier: EUPL-1.2
async function loadAgents(){
  let data;
  try{ data=await (await fetch("/api/agents")).json(); }catch(e){ return; }
  const wrap=$("#agentList"); wrap.innerHTML="";
  for(const a of (data.agents||[])){
    const el=document.createElement("div"); el.className="agent";
    const chips=(a.channels||[]).length
      ? `<div class="chips">${a.channels.map(c=>`<span class="chip" data-c="${c}">${c}</span>`).join("")}</div>`
      : `<div class="none">in geen enkel kanaal</div>`;
    el.innerHTML=`<div class="nm">${a.handle}</div><div class="rol">${a.rol||""}</div>${chips}`;
    el.querySelectorAll(".chip").forEach(ch=>ch.onclick=()=>{
      const c=channels.find(x=>x.name===ch.dataset.c);
      if(c){ selectChannel(c); closeAgents();
        input.value="@"+a.handle+" "; input.focus(); }
    });
    wrap.appendChild(el);
  }
}
function closeAgents(){ $("#agentsDrawer").classList.remove("open"); }
function closeRepos(){ $("#reposDrawer").classList.remove("open"); }

async function sendTo(channelName, text){
  const c = channels.find(x=>x.name===channelName);
  if(!c){ toast("kanaal #"+channelName+" bestaat niet"); return false; }
  const r = await fetch("/api/send",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({channel:c.id, content:text})});
  const j = await r.json().catch(()=>({}));
  if(!r.ok||j.error){ toast(j.error||"versturen mislukt"); return false; }
  return true;
}
async function reviewPR(repo, num, title, url){
  const ok = await sendTo("review", `@reviewer bekijk PR ${repo}#${num} — ${title}\n${url}`);
  if(ok){ closeRepos(); const c=channels.find(x=>x.name==="review");
    if(c) selectChannel(c); toast("review aangevraagd in #review"); }
}
async function openRepos(){
  $("#repoTitle").textContent="Repo's · GitHub";
  const view=$("#repoView"); view.innerHTML='<div class="agenthint">laden…</div>';
  $("#reposDrawer").classList.add("open");
  let d; try{ d=await (await fetch("/api/repos")).json(); }
  catch(e){ view.innerHTML='<div class="agenthint">GitHub onbereikbaar.</div>'; return; }
  if(d.error){ view.innerHTML=`<div class="agenthint">${d.error}</div>`; return; }
  view.innerHTML="";
  for(const r of (d.repos||[])){
    const el=document.createElement("div"); el.className="rrow";
    const [own,nm]=r.full_name.split("/");
    el.innerHTML=`<span class="badge">${r.open_issues} open</span>`+
      `<div class="rn"><span class="own">${own}/</span>${nm}${r.private?" 🔒":""}</div>`+
      `<div class="rd">${r.description||"—"}</div>`;
    el.onclick=()=>showRepo(r.full_name);
    view.appendChild(el);
  }
}
async function showRepo(full){
  $("#repoTitle").textContent=full;
  const view=$("#repoView");
  view.innerHTML='<span class="rback">← repo\'s</span><div class="agenthint">PR\'s laden…</div>';
  view.querySelector(".rback").onclick=openRepos;
  let d; try{ d=await (await fetch("/api/prs?repo="+encodeURIComponent(full))).json(); }
  catch(e){ return; }
  const back='<span class="rback">← repo\'s</span>';
  if(d.error){ view.innerHTML=back+`<div class="agenthint">${d.error}</div>`; view.querySelector(".rback").onclick=openRepos; return; }
  const prs=d.prs||[];
  view.innerHTML=back+(prs.length?"":'<div class="agenthint">Geen open PR\'s.</div>');
  view.querySelector(".rback").onclick=openRepos;
  for(const p of prs){
    const el=document.createElement("div"); el.className="rrow";
    el.innerHTML=`<span class="badge">#${p.number}</span>`+
      `<div class="rn">${p.title}${p.draft?" · concept":""}</div>`+
      `<div class="rd">${p.head} → ${p.base} · door ${p.author}</div>`;
    el.onclick=()=>showPR(full, p.number);
    view.appendChild(el);
  }
}
async function showPR(repo, num){
  const view=$("#repoView");
  view.innerHTML='<span class="rback">← PR\'s</span><div class="agenthint">laden…</div>';
  view.querySelector(".rback").onclick=()=>showRepo(repo);
  let p; try{ p=await (await fetch(`/api/pr?repo=${encodeURIComponent(repo)}&num=${num}`)).json(); }
  catch(e){ return; }
  if(p.error){ view.innerHTML=`<span class="rback">← PR's</span><div class="agenthint">${p.error}</div>`;
    view.querySelector(".rback").onclick=()=>showRepo(repo); return; }
  const files=(p.files||[]).map(f=>`<div class="file">${f.status[0].toUpperCase()} ${f.filename} `+
    `<span class="add">+${f.additions}</span> <span class="del">−${f.deletions}</span></div>`).join("");
  const d=document.createElement("div"); d.className="prdet";
  d.innerHTML=`<span class="rback">← PR\'s</span>`+
    `<div class="rn" style="margin:.3rem 0">#${p.number} · ${p.title}</div>`+
    `<div class="st">${p.head} → ${p.base} · door ${p.author} · `+
    `<span class="add">+${p.additions}</span> <span class="del">−${p.deletions}</span> in ${p.changed_files} bestanden</div>`+
    `${files}`+
    `<div style="margin-top:.6rem"><a class="gh" href="${p.url}" target="_blank" rel="noopener">op GitHub openen ↗</a></div>`+
    `<button class="rev">🔍 Laat @reviewer kijken</button>`;
  view.innerHTML=""; view.appendChild(d);
  d.querySelector(".rback").onclick=()=>showRepo(repo);
  d.querySelector(".rev").onclick=()=>reviewPR(repo, p.number, p.title, p.url);
}

// UI-bindings
$("#switch").onclick=()=>$("#drawer").classList.add("open");
$("#agentsBtn").onclick=()=>{ loadAgents(); $("#agentsDrawer").classList.add("open"); };
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
  const ok=await send(t);
  $("#send").disabled=false;
  if(ok){ input.value=""; input.style.height="auto"; await refresh(true); }
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
