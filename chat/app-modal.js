// SPDX-License-Identifier: EUPL-1.2
// UI-helpers voor de mention-pop-up, apart van app.js zodat die ≤200 regels blijft.

// Generieke ja/nee-pop-up → Promise<bool>.
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

// Voeg een agent toe aan een kanaal → true bij succes (toont zelf de serverfout).
async function addAgent(name, cid){
  const rr=await fetch("/api/channel/add-member",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({channel:cid, name:name})}).catch(()=>null);
  if(rr && rr.ok){ toast("@"+name+" toegevoegd ✓"); return true; }
  const jj=rr?await rr.json().catch(()=>({})):{}; toast(jj.error||"toevoegen mislukt"); return false;
}
