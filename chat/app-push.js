// SPDX-License-Identifier: EUPL-1.2
// Web Push: subscribing to phone notifications. A separate file (app-ui.js sat
// at the 200-line limit). Loads after app.js/app-ui.js, so `toast` is available.
function urlB64ToUint8Array(b64){
  const pad="=".repeat((4-b64.length%4)%4);
  const s=(b64+pad).replace(/-/g,"+").replace(/_/g,"/");
  const raw=atob(s); const arr=new Uint8Array(raw.length);
  for(let i=0;i<raw.length;i++) arr[i]=raw.charCodeAt(i);
  return arr;
}
// Compare the key an existing subscription was created with against the key the
// server serves NOW. Without this check a stale subscription survives a VAPID
// rotation: the browser reuses it, every send gets a 403 and the device is
// silently dead.
function sameServerKey(buf, wanted){
  if(!buf) return false;
  const cur=new Uint8Array(buf);
  if(cur.length!==wanted.length) return false;
  for(let i=0;i<cur.length;i++) if(cur[i]!==wanted[i]) return false;
  return true;
}
// Make sure the server knows a valid subscription, and POST it. One path for the
// first subscribe AND for silent self-repair: a revoked subscription
// (getSubscription()===null) or a key mismatch (rotation) leads to subscribing
// again instead of failing quietly.
async function ensurePushSubscription(){
  const {key}=await (await fetch("/api/push/vapid")).json();
  if(!key) throw new Error("no VAPID key");
  const wanted=urlB64ToUint8Array(key);
  const reg=await navigator.serviceWorker.ready;
  let sub=await reg.pushManager.getSubscription();
  if(sub && !sameServerKey(sub.options && sub.options.applicationServerKey, wanted)){
    await sub.unsubscribe().catch(()=>{}); sub=null;  // the VAPID pair changed
  }
  if(!sub){
    sub=await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:wanted});
  }
  const r=await postJSON("/api/push/subscribe", sub);
  if(!r.ok) throw new Error("the subscribe POST failed");
  return sub;
}
async function enablePush(btn){
  if(!("serviceWorker" in navigator) || !("PushManager" in window)){ toast("push not supported"); return; }
  try{
    const perm=await Notification.requestPermission();
    // "denied" here means the browser did not even ask — it remembers a previous
    // refusal for this origin. "default" means the prompt was dismissed. They
    // need different advice, and neither is a reason to fall silent.
    if(perm==="denied"){ explainBlocked(); return; }
    if(perm!=="granted"){ toast("notifications not allowed — tap 🔔 to try again"); return; }
    await ensurePushSubscription();
    toast("notifications on ✓"); if(btn) btn.remove();
  }catch(e){
    // De fout ZEGGEN, niet inslikken. Op 2026-09-13 kostte dit een dag: de
    // server zag /api/push/vapid binnenkomen en daarna niets meer, en dit
    // catch-blok gooide precies de zin weg die verteld zou hebben waaróm.
    // De naam is het bruikbare deel — NotAllowedError (permissie),
    // AbortError (de pushdienst is onbereikbaar) en InvalidAccessError (de
    // sleutel deugt niet) vragen elk iets anders van je.
    toast("aanmelden mislukt: " + foutTekst(e), 9000);
  }
}
function foutTekst(e){
  if(!e) return "onbekende fout";
  const naam = e.name || "";
  const bericht = e.message || String(e);
  return naam && naam !== "Error" ? naam + " — " + bericht : bericht;
}
function bell(title, onclick){
  const pb=document.createElement("button");
  pb.id="pushBtn"; pb.textContent="🔔"; pb.title=title;
  pb.onclick=()=>onclick(pb);
  document.querySelector("header").appendChild(pb);
  return pb;
}
// Once a site is blocked, `requestPermission()` resolves to "denied" WITHOUT
// showing a prompt, so a button that calls it again is a button that does
// nothing. The only way back is the browser's own site settings, so say that.
function explainBlocked(){
  toast("notifications are blocked for this site. Chrome: ⋮ → ⓘ next to the "
      + "address → notifications → allow. Then reopen the app.", 9000);
}
// Three permission states, three behaviours, and none of them silent. Measured
// 2026-09-13: Mark turned notifications on and nothing happened — the access log
// showed the phone polling normally while it never once asked for the VAPID key.
// That is what "denied" used to look like from here: no button, no message, no
// request. A phone that cannot notify has to SAY it cannot notify, because the
// alternative is indistinguishable from a phone that simply has no news.
if("serviceWorker" in navigator && "PushManager" in window && "Notification" in window){
  if(Notification.permission==="granted"){
    // Already granted: quietly ensure the server knows our (correct) subscription.
    // NOT silently on failure: a subscription can expire (reinstall, new browser
    // context, FCM prunes it) and then you get no notifications and no hint why.
    ensurePushSubscription().catch((e) => {
      // Stil falen is hier het duurst: meldingen staan "aan", er komt niets
      // binnen, en niets op het scherm zegt waarom. De bel komt terug MET de
      // reden erin, zodat een volgende keer een diagnose is en geen zoektocht.
      const b = bell("meldingen staan aan, maar dit toestel is niet aangemeld — tik om te herstellen",
                     (btn)=>enablePush(btn));
      b.dataset.reden = foutTekst(e);
      if(typeof toast === "function") toast("aanmelden mislukt: " + foutTekst(e), 9000);
    });
  }else if(Notification.permission==="denied"){
    bell("notifications are blocked for this site — tap to see how to allow them",
         explainBlocked);
  }else{
    bell("turn notifications on", (b)=>enablePush(b));
  }
}
