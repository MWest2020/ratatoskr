// SPDX-License-Identifier: EUPL-1.2
// The Repos drawer: repo list, PR list, PR detail, and "let @reviewer look".
// Separate from app-ui.js so both stay under the 200-line convention.
//
// Everything coming from GitHub here — repo description, PR title, branch name,
// file name, author — is rendered with `el`/`add` from app-modal.js, so through
// textContent. A PR title can be set by anyone who opens a PR on a public repo;
// with innerHTML that would be HTML in Mark's PWA.
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
  if(d.error){ view.innerHTML=""; add(view, el("div","agenthint", d.error)); return; }
  view.innerHTML="";
  for(const r of (d.repos||[])){
    const row=document.createElement("div"); row.className="rrow";
    const [own,nm]=String(r.full_name).split("/");
    add(row, el("span","badge", `${r.open_issues} open`),
             add(el("div","rn"), el("span","own", own+"/"), nm+(r.private?" 🔒":"")),
             el("div","rd", r.description||"—"));
    row.onclick=()=>showRepo(r.full_name);
    view.appendChild(row);
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
  if(d.error){ view.innerHTML=back; add(view, el("div","agenthint", d.error));
    view.querySelector(".rback").onclick=openRepos; return; }
  const prs=d.prs||[];
  view.innerHTML=back+(prs.length?"":'<div class="agenthint">Geen open PR\'s.</div>');
  view.querySelector(".rback").onclick=openRepos;
  for(const p of prs){
    const row=document.createElement("div"); row.className="rrow";
    add(row, el("span","badge", "#"+p.number),
             el("div","rn", p.title+(p.draft?" · concept":"")),
             el("div","rd", `${p.head} → ${p.base} · door ${p.author}`));
    row.onclick=()=>showPR(full, p.number);
    view.appendChild(row);
  }
}
async function showPR(repo, num){
  const view=$("#repoView");
  view.innerHTML='<span class="rback">← PR\'s</span><div class="agenthint">laden…</div>';
  view.querySelector(".rback").onclick=()=>showRepo(repo);
  let p; try{ p=await (await fetch(`/api/pr?repo=${encodeURIComponent(repo)}&num=${num}`)).json(); }
  catch(e){ return; }
  if(p.error){ view.innerHTML=""; add(view, el("span","rback","← PR's"), el("div","agenthint", p.error));
    view.querySelector(".rback").onclick=()=>showRepo(repo); return; }
  const d=document.createElement("div"); d.className="prdet";
  const rn=el("div","rn", `#${p.number} · ${p.title}`); rn.style.margin=".3rem 0";
  add(d, el("span","rback","← PR\'s"), rn,
         add(el("div","st"), `${p.head} → ${p.base} · door ${p.author} · `,
             el("span","add","+"+p.additions), " ", el("span","del","−"+p.deletions),
             ` in ${p.changed_files} bestanden`));
  for(const f of (p.files||[]))
    add(d, add(el("div","file"), `${String(f.status)[0].toUpperCase()} ${f.filename} `,
               el("span","add","+"+f.additions), " ", el("span","del","−"+f.deletions)));
  // href only when it really is a GitHub URL; a javascript: URL from the payload
  // would otherwise become clickable.
  const wrap=document.createElement("div"); wrap.style.marginTop=".6rem";
  const a=el("a","gh","op GitHub openen ↗");
  a.href=/^https:\/\/github\.com\//.test(p.url||"") ? p.url : "https://github.com/";
  a.target="_blank"; a.rel="noopener";
  add(d, add(wrap, a), el("button","rev","🔍 Laat @reviewer kijken"));
  view.innerHTML=""; view.appendChild(d);
  d.querySelector(".rback").onclick=()=>showRepo(repo);
  d.querySelector(".rev").onclick=()=>reviewPR(repo, p.number, p.title, p.url);
}

