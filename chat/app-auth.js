// SPDX-License-Identifier: EUPL-1.2
// Sessie in plaats van apparaat-token. De server zet een HttpOnly-cookie, dus
// JavaScript ziet die niet en kan hem ook niet lekken; wat de app wél nodig
// heeft is het sessiegebonden token dat bij elk statuswijzigend verzoek mee moet.
//
// Een 401 betekent "jij mag hier niet (meer)" en is iets anders dan een
// netwerkfout, die "ik kan er niet bij" betekent. Ze verdienen een ander
// antwoord: het eerste stuurt naar inloggen (en wist wat er lokaal bewaard is,
// zodat de volgende persoon op dit apparaat niets van de vorige leest), het
// tweede laat de app staan waar hij staat.

let csrfToken = "";

/** De sessie, of `null` bij een 401 (echt uitgelogd), of `undefined` als we er
    niet bij konden. Dat onderscheid is de hele grap: uitgelogd stuurt naar
    inloggen, geen netwerk laat de app staan waar hij staat. */
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

/** Naar de inlogpagina, met een verwijzing terug naar waar je was. */
function goToLogin(){
  if(typeof clearSnapshots === "function") clearSnapshots();
  const back = location.pathname + location.search + location.hash;
  location.replace("/login?terug=" + encodeURIComponent(back));
}

/** Alleen aanroepen bij een échte 401, niet bij een netwerkfout. */
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
    // Sessietoken kwijt (bijvoorbeeld na een herstart van de app): ophalen en
    // één keer opnieuw. Lukt dat niet, dan is de sessie echt weg.
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

// Wie ben je, en mag je uitnodigen — de eigenaar wel, de rest niet.
function showWhoYouAre(session){
  const who = $("#whoAmI");
  if(who && session && session.naam) who.textContent = "ingelogd als " + session.naam;
  const invite = $("#inviteBtn");
  if(invite && session && session.eigenaar){
    invite.hidden = false;
    invite.onclick = async () => {
      const r = await postJSON("/api/uitnodiging", {});
      const d = await r.json().catch(() => ({}));
      if(!r.ok || !d.pad){ toast(d.error || "uitnodigen mislukte"); return; }
      const link = location.origin + d.pad;
      try{ await navigator.clipboard.writeText(link); toast("uitnodiging gekopieerd"); }
      catch(e){ toast(link); }   // geen klembord: dan maar tonen
    };
  }
  const pw = $("#passwordBtn");
  if(pw) pw.onclick = changePassword;
  const out = $("#logoutBtn");
  if(out) out.onclick = () => logOut(false);
}

/** Wachtwoord wijzigen. Twee velden in een pop-up; window.prompt kan niet, dat
    blokkeren browsers in een geïnstalleerde PWA. */
function changePassword(){
  const ov = el("div", "modal-ov");
  const box = el("div", "modal");
  const current = el("input", "modal-in"); current.type = "password";
  current.placeholder = "huidig wachtwoord"; current.autocomplete = "current-password";
  const fresh = el("input", "modal-in"); fresh.type = "password";
  fresh.placeholder = "nieuw wachtwoord (min. 12 tekens)";
  fresh.autocomplete = "new-password";
  const row = el("div", "modal-row");
  const ok = el("button", "modal-add", "Wijzigen");
  const cancel = el("button", "modal-cancel", "Annuleren");
  const close = () => ov.remove();
  cancel.onclick = close;
  ov.onclick = (e) => { if(e.target === ov) close(); };
  ok.onclick = async () => {
    ok.disabled = true;
    const r = await postJSON("/api/wachtwoord",
      { huidig: current.value, nieuw: fresh.value });
    const d = await r.json().catch(() => ({}));
    ok.disabled = false;
    if(!r.ok){ toast(d.error || "wijzigen mislukte"); return; }
    // De server gaf een nieuwe sessie; die zit al in de cookie, het token hier.
    if(d.csrf) csrfToken = d.csrf;
    close();
    toast("wachtwoord gewijzigd — andere apparaten zijn uitgelogd");
  };
  add(row, ok, cancel);
  add(box, el("div", "modal-t", "Wachtwoord wijzigen"),
      el("div", "modal-sub", "Alle andere apparaten worden uitgelogd."),
      current, fresh, row);
  add(ov, box);
  document.body.append(ov);
  setTimeout(() => current.focus(), 50);
}
