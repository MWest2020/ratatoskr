// SPDX-License-Identifier: EUPL-1.2
// UI helpers for the mention pop-up, separate from app.js so that stays ≤200
// lines. Also: the DOM builders the rest of the app uses. Loaded before app.js and
// app-ui.js, so `el` and `add` are available there.

// el(tag, class, text) — text ALWAYS goes through textContent, never innerHTML.
// That is not a style choice: PR titles, branch names, file names and repo
// descriptions come from GitHub and can be set by anyone who opens a PR on a
// public repo. With innerHTML that runs as HTML in Mark's PWA, where the device
// token sits in localStorage.
function el(tag, cls, text){
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = String(text);
  return n;
}

// add(parent, ...children) — strings become text nodes, not markup.
function add(parent, ...kids){
  for (const k of kids) {
    if (k === null || k === undefined) continue;
    parent.appendChild(typeof k === "string" ? document.createTextNode(k) : k);
  }
  return parent;
}

// Generic yes/no pop-up → Promise<bool>.
function modalConfirm(title, sub, okLabel){
  return new Promise(resolve=>{
    const ov=document.createElement("div"); ov.className="modal-ov";
    const box=document.createElement("div"); box.className="modal";
    const t=document.createElement("div"); t.className="modal-t"; t.textContent=title;
    const s=document.createElement("div"); s.className="modal-sub"; s.textContent=sub;
    const row=document.createElement("div"); row.className="modal-row";
    const ok=document.createElement("button"); ok.className="modal-add"; ok.textContent=okLabel;
    const cancel=document.createElement("button"); cancel.className="modal-cancel"; cancel.textContent="Annuleren";
    const done=v=>{ ov.remove(); resolve(v); };
    cancel.onclick=()=>done(false);
    ov.onclick=e=>{ if(e.target===ov) done(false); };
    ok.onclick=()=>done(true);
    row.append(ok, cancel); box.append(t, s, row); ov.append(box); document.body.append(ov);
  });
}

// Add an agent to a channel → true on success (shows the server error itself).
async function addAgent(name, cid){
  const rr=await postJSON("/api/channel/add-member",{channel:cid, name:name}).catch(()=>null);
  if(rr && rr.ok){ toast("@"+name+" toegevoegd ✓"); return true; }
  const jj=rr?await rr.json().catch(()=>({})):{}; toast(jj.error||"toevoegen mislukt"); return false;
}
