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
    if(perm!=="granted"){ toast("notifications not allowed"); return; }
    await ensurePushSubscription();
    toast("notifications on ✓"); if(btn) btn.remove();
  }catch(e){ toast("subscribing failed"); }
}
if("serviceWorker" in navigator && "PushManager" in window && "Notification" in window){
  if(Notification.permission==="granted"){
    // Already granted: quietly ensure the server knows our (correct) subscription.
    // NOT silently on failure: a subscription can expire (reinstall, new browser
    // context, FCM prunes it) and then you get no notifications and no hint why.
    // Measured 2026-09-12 — Mark: "ook geen meldingen". So on failure the bell
    // comes back: something to press instead of silence.
    ensurePushSubscription().catch(()=>{
      const pb=document.createElement("button");
      pb.id="pushBtn"; pb.textContent="🔔"; pb.title="notifications are off — tap to fix";
      pb.onclick=()=>enablePush(pb);
      document.querySelector("header").appendChild(pb);
    });
  }else if(Notification.permission!=="denied"){
    // Not decided yet: show a 🔔 button.
    const pb=document.createElement("button");
    pb.id="pushBtn"; pb.textContent="🔔"; pb.title="turn notifications on";
    pb.onclick=()=>enablePush(pb);
    document.querySelector("header").appendChild(pb);
  }
}
