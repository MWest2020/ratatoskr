// SPDX-License-Identifier: EUPL-1.2
// Schrijf-token per apparaat. De server zet het NOOIT in de pagina: wie de
// pagina kan ophalen (elke tailnet-node) zou het dan kunnen lezen, en juist
// daartegen is het bedoeld. Dus: de gebruiker voert het één keer in, het blijft
// in localStorage van dít apparaat, en elke schrijf-fetch loopt hierlangs.
const TOKEN_KEY = "boomhuis.appToken";

function appToken(){ try { return localStorage.getItem(TOKEN_KEY) || ""; } catch(e){ return ""; } }
function setAppToken(t){ try { localStorage.setItem(TOKEN_KEY, t); } catch(e){} }

// Invoer via een eigen pop-up, NIET via window.prompt: in een geïnstalleerde PWA
// (standalone) blokkeren browsers prompt(), en de aanroep klapt. Het gevolg was een
// misleidende "netwerkfout" terwijl er niets met het netwerk mis was — waargenomen
// 2026-09-06 op Marks toestel, waar helemaal geen invoervenster verscheen.
function askToken(){
  return new Promise(resolve=>{
    const ov=document.createElement("div"); ov.className="modal-ov";
    const box=document.createElement("div"); box.className="modal";
    const t=document.createElement("div"); t.className="modal-t";
    t.textContent="Schrijf-token voor dit apparaat";
    const sub=document.createElement("div"); sub.className="modal-sub";
    sub.textContent="Lezen kan zonder. Voor versturen vraagt de server eenmalig een token; "
                  + "het blijft daarna op dit apparaat staan.";
    const inp=document.createElement("input"); inp.className="modal-in"; inp.type="password";
    inp.autocomplete="off"; inp.placeholder="token";
    const row=document.createElement("div"); row.className="modal-row";
    const ok=document.createElement("button"); ok.className="modal-add"; ok.textContent="Opslaan";
    const cancel=document.createElement("button"); cancel.className="modal-cancel";
    cancel.textContent="Annuleren";
    const done=v=>{ ov.remove(); resolve(v); };
    cancel.onclick=()=>done("");
    ov.onclick=e=>{ if(e.target===ov) done(""); };
    ok.onclick=()=>done((inp.value||"").trim());
    inp.onkeydown=e=>{ if(e.key==="Enter") ok.click(); };
    row.append(ok, cancel); box.append(t, sub, inp, row); ov.append(box);
    document.body.append(ov); setTimeout(()=>inp.focus(), 50);
  });
}

// POST met token; bij 401 één keer om het token vragen en opnieuw proberen.
async function postJSON(path, body){
  const send = () => fetch(path, {
    method: "POST",
    headers: Object.assign({"Content-Type": "application/json"},
                           appToken() ? {"X-App-Token": appToken()} : {}),
    body: JSON.stringify(body),
  });
  let r = await send();
  if (r.status !== 401) return r;
  const t = await askToken();
  if (!t) return r;                 // geannuleerd: 401 teruggeven, de beller meldt het
  setAppToken(t);
  r = await send();
  // Push-registratie faalt stil zolang er geen token was; nu er wel een is,
  // meteen zelfherstellen zodat meldingen niet stiekem uit blijven.
  if (r.ok && typeof ensurePushSubscription === "function") {
    ensurePushSubscription().catch(() => {});
  }
  return r;
}
