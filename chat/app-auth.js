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
async function sessieOphalen(){
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
function naarInloggen(){
  if(typeof wisSnapshots === "function") wisSnapshots();
  const terug = location.pathname + location.search + location.hash;
  location.replace("/login?terug=" + encodeURIComponent(terug));
}

/** Alleen aanroepen bij een échte 401, niet bij een netwerkfout. */
function afgemeld(){
  naarInloggen();
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
  if(r.status === 401){ afgemeld(); }
  if(r.status === 403 && !csrfToken){
    // Sessietoken kwijt (bijvoorbeeld na een herstart van de app): ophalen en
    // één keer opnieuw. Lukt dat niet, dan is de sessie echt weg.
    const s = await sessieOphalen();
    if(s){
      return await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify(body),
      });
    }
    afgemeld();
  }
  return r;
}

async function uitloggen(overal){
  try{ await postJSON("/api/uitloggen", { overal: !!overal }); }catch(e){}
  if(typeof wisSnapshots === "function") wisSnapshots();
  location.replace("/login");
}

// Wie ben je, en mag je uitnodigen — de eigenaar wel, de rest niet.
function toonWieJeBent(sessie){
  const wie = $("#wieBenJe");
  if(wie && sessie && sessie.naam) wie.textContent = "ingelogd als " + sessie.naam;
  const uitnodig = $("#uitnodigBtn");
  if(uitnodig && sessie && sessie.eigenaar){
    uitnodig.hidden = false;
    uitnodig.onclick = async () => {
      const r = await postJSON("/api/uitnodiging", {});
      const d = await r.json().catch(() => ({}));
      if(!r.ok || !d.pad){ toast(d.error || "uitnodigen mislukte"); return; }
      const link = location.origin + d.pad;
      try{ await navigator.clipboard.writeText(link); toast("uitnodiging gekopieerd"); }
      catch(e){ toast(link); }   // geen klembord: dan maar tonen
    };
  }
  const uit = $("#uitlogBtn");
  if(uit) uit.onclick = () => uitloggen(false);
}
