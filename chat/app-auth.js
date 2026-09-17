// SPDX-License-Identifier: MIT
// A session instead of a device token. The server sets an HttpOnly cookie, so
// JavaScript never sees it and cannot leak it; what the app does need is the
// session-bound token that has to accompany every state-changing request.
//
// A 401 means "you may not be here (any more)" and is something other than a
// network error, which means "I cannot reach it". They deserve different answers:
// the first sends you to the login page (and clears what is stored locally, so
// the next person on this device reads nothing of the previous one), the second
// leaves the app where it is.

let csrfToken = "";

/** The session, or `null` on a 401 (really logged out), or `undefined` when we
    could not reach it. That distinction is the whole point: logged out goes to the
    login page, no network leaves the app where it is. */
async function fetchSession(){
  let r;
  try{ r = await fetch("/api/sessie", { headers: { "Accept": "application/json" } }); }
  catch(e){ return undefined; }
  if(r.status === 401) return null;
  if(!r.ok) return undefined;
  try{
    const s = await r.json();
    csrfToken = s.csrf || "";
    return s;
  }catch(e){ return undefined; }
}

/** To the login page, with a pointer back to where you were. */
function goToLogin(){
  if(typeof clearSnapshots === "function") clearSnapshots();
  const back = location.pathname + location.search + location.hash;
  location.replace("/login?terug=" + encodeURIComponent(back));
}

/** Only call this on a real 401, not on a network error. */
function loggedOut(){
  goToLogin();
}

async function postJSON(path, body){
  const r = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    body: JSON.stringify(body),
  });
  if(r.status === 401){ loggedOut(); }
  if(r.status === 403 && !csrfToken){
    // Session token lost (after an app restart, for instance): fetch it and try
    // once more. If that fails, the session is really gone.
    const s = await fetchSession();
    if(s){
      return await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify(body),
      });
    }
    loggedOut();
  }
  return r;
}

async function logOut(everywhere){
  try{ await postJSON("/api/uitloggen", { overal: !!everywhere }); }catch(e){}
  if(typeof clearSnapshots === "function") clearSnapshots();
  location.replace("/login");
}

// Who are you, and may you invite — the owner may, the rest may not.
function showWhoYouAre(session){
  const who = $("#whoAmI");
  if(who && session && session.naam) who.textContent = "signed in as " + session.naam;
  const invite = $("#inviteBtn");
  if(invite && session && session.eigenaar){
    invite.hidden = false;
    invite.onclick = async () => {
      const r = await postJSON("/api/uitnodiging", {});
      const d = await r.json().catch(() => ({}));
      if(!r.ok || !d.pad){ toast(d.error || "inviting failed"); return; }
      const link = location.origin + d.pad;
      try{ await navigator.clipboard.writeText(link); toast("invitation copied"); }
      catch(e){ toast(link); }   // no clipboard: then just show it
    };
  }
  const pw = $("#passwordBtn");
  if(pw) pw.onclick = changePassword;
  const out = $("#logoutBtn");
  if(out) out.onclick = () => logOut(false);
}

/** Change your password. Two fields in a pop-up; window.prompt is out, browsers
    block that in an installed PWA. */
function changePassword(){
  const ov = el("div", "modal-ov");
  const box = el("div", "modal");
  const current = el("input", "modal-in"); current.type = "password";
  current.placeholder = "current password"; current.autocomplete = "current-password";
  const fresh = el("input", "modal-in"); fresh.type = "password";
  fresh.placeholder = "new password (min. 12 characters)";
  fresh.autocomplete = "new-password";
  const row = el("div", "modal-row");
  const ok = el("button", "modal-add", "Change");
  const cancel = el("button", "modal-cancel", "Cancel");
  const close = () => ov.remove();
  cancel.onclick = close;
  ov.onclick = (e) => { if(e.target === ov) close(); };
  ok.onclick = async () => {
    ok.disabled = true;
    const r = await postJSON("/api/wachtwoord",
      { huidig: current.value, nieuw: fresh.value });
    const d = await r.json().catch(() => ({}));
    ok.disabled = false;
    if(!r.ok){ toast(d.error || "the change failed"); return; }
    // The server gave a new session; it is already in the cookie, the token here.
    if(d.csrf) csrfToken = d.csrf;
    close();
    toast("password changed — other devices have been signed out");
  };
  add(row, ok, cancel);
  add(box, el("div", "modal-t", "Change password"),
      el("div", "modal-sub", "All other devices will be signed out."),
      current, fresh, row);
  add(ov, box);
  document.body.append(ov);
  setTimeout(() => current.focus(), 50);
}
