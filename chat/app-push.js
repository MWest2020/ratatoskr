// SPDX-License-Identifier: EUPL-1.2
// Web Push: aanmelden voor telefoon-notificaties. Apart bestand (app-ui.js zat op
// de 200-regel-grens). Laadt ná app.js/app-ui.js, dus `toast` is beschikbaar.
function urlB64ToUint8Array(b64){
  const pad="=".repeat((4-b64.length%4)%4);
  const s=(b64+pad).replace(/-/g,"+").replace(/_/g,"/");
  const raw=atob(s); const arr=new Uint8Array(raw.length);
  for(let i=0;i<raw.length;i++) arr[i]=raw.charCodeAt(i);
  return arr;
}
// Vergelijk de key waarmee een bestaande subscription is aangemaakt met de key die
// de server NU serveert. Zonder deze check overleeft een verouderde subscription
// een VAPID-rotatie: de browser hergebruikt 'm, elke send krijgt 403 en het
// toestel is stil dood.
function sameServerKey(buf, wanted){
  if(!buf) return false;
  const cur=new Uint8Array(buf);
  if(cur.length!==wanted.length) return false;
  for(let i=0;i<cur.length;i++) if(cur[i]!==wanted[i]) return false;
  return true;
}
// Zorg dat er een geldige subscription bij de server bekend is en POST 'm. Eén pad
// voor de eerste aanmelding én het stille zelfherstel: een ingetrokken subscription
// (getSubscription()===null) of een key-mismatch (rotatie) leidt tot opnieuw
// abonneren i.p.v. stil falen.
async function ensurePushSubscription(){
  const {key}=await (await fetch("/api/push/vapid")).json();
  if(!key) throw new Error("geen VAPID-key");
  const wanted=urlB64ToUint8Array(key);
  const reg=await navigator.serviceWorker.ready;
  let sub=await reg.pushManager.getSubscription();
  if(sub && !sameServerKey(sub.options && sub.options.applicationServerKey, wanted)){
    await sub.unsubscribe().catch(()=>{}); sub=null;  // VAPID-paar gewijzigd
  }
  if(!sub){
    sub=await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:wanted});
  }
  const r=await fetch("/api/push/subscribe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(sub)});
  if(!r.ok) throw new Error("subscribe-POST faalde");
  return sub;
}
async function enablePush(btn){
  if(!("serviceWorker" in navigator) || !("PushManager" in window)){ toast("push niet ondersteund"); return; }
  try{
    const perm=await Notification.requestPermission();
    if(perm!=="granted"){ toast("meldingen niet toegestaan"); return; }
    await ensurePushSubscription();
    toast("meldingen aan ✓"); if(btn) btn.remove();
  }catch(e){ toast("aanmelden mislukt"); }
}
if("serviceWorker" in navigator && "PushManager" in window && "Notification" in window){
  if(Notification.permission==="granted"){
    // Al toegestaan: stil borgen dat de server onze (juiste) subscription kent.
    ensurePushSubscription().catch(()=>{});
  }else if(Notification.permission!=="denied"){
    // Nog niet beslist: toon een 🔔-knop.
    const pb=document.createElement("button");
    pb.id="pushBtn"; pb.textContent="🔔"; pb.title="meldingen aanzetten";
    pb.onclick=()=>enablePush(pb);
    document.querySelector("header").appendChild(pb);
  }
}
