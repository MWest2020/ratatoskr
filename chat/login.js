// SPDX-License-Identifier: EUPL-1.2
// Eén pagina, drie situaties: inloggen, de eerste persoon aanmaken (setup), en
// een uitnodiging gebruiken. Ze verschillen alleen in welk endpoint er
// aangeroepen wordt en welke velden je ziet — een aparte pagina per geval
// levert drie keer hetzelfde formulier op.

const params = new URLSearchParams(location.search);
const setupToken = params.get("setup") || "";
const uitnodiging = params.get("uitnodiging") || "";
const terug = params.get("terug") || "/";

const $ = (id) => document.getElementById(id);
const melding = (tekst) => { $("melding").textContent = tekst; $("melding").hidden = !tekst; };

let modus = "inloggen";
if (uitnodiging) modus = "uitnodiging";
else if (setupToken) modus = "setup";

async function bepaalModus(){
  if (modus !== "inloggen") return;
  // Verse installatie zonder setup-link in de URL: dan is het enige zinnige
  // scherm "maak de eigenaar aan", met het oude gedeelde token als sleutel.
  try{
    const r = await fetch("/api/status");
    const s = await r.json();
    if ((s.personen || 0) === 0){ modus = "setup"; $("tokenveld").hidden = false; }
  }catch(e){ /* laat het inlogscherm staan */ }
}

function toon(){
  const titels = {
    inloggen: ["Inloggen", "Ratatoskr is alleen voor mensen met een account."],
    setup: ["Eerste account", "Dit boomhuis heeft nog niemand. Maak de eigenaar aan."],
    uitnodiging: ["Welkom", "Kies een naam en een wachtwoord van minstens 12 tekens."],
  };
  const [t, u] = titels[modus];
  $("titel").textContent = t;
  $("uitleg").textContent = u;
  $("knop").textContent = modus === "inloggen" ? "Inloggen" : "Account maken";
  $("naam").autocomplete = modus === "inloggen" ? "username" : "off";
  $("wachtwoord").autocomplete = modus === "inloggen" ? "current-password" : "new-password";
}

async function verstuur(e){
  e.preventDefault();
  melding("");
  $("knop").disabled = true;
  const body = { naam: $("naam").value, wachtwoord: $("wachtwoord").value };
  let pad = "/api/login";
  if (modus === "setup"){ pad = "/api/setup"; body.token = setupToken || $("token").value; }
  if (modus === "uitnodiging"){ pad = "/api/uitnodiging/gebruik"; body.token = uitnodiging; }
  if (!$("codeveld").hidden) body.code = $("code").value;

  try{
    const r = await fetch(pad, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const d = await r.json().catch(() => ({}));
    if (r.ok){ location.replace(terug.startsWith("/") ? terug : "/"); return; }
    if (d.totp){
      // Naam en wachtwoord klopten; nu de tweede factor. Het veld verschijnt
      // pas hier, zodat wie geen tweede factor heeft er ook geen ziet.
      $("codeveld").hidden = false;
      $("code").focus();
      melding(d.error === "code nodig" ? "Vul de code uit je app in." : "Die code klopt niet.");
    } else if (r.status === 429){
      melding("Te veel pogingen. Probeer het over " + (d.wacht || 60) + " seconden opnieuw.");
    } else {
      melding(d.error || "Er ging iets mis.");
    }
  }catch(err){
    melding("Geen verbinding met het boomhuis — staat Tailscale aan?");
  }finally{
    $("knop").disabled = false;
  }
}

(async function start(){
  await bepaalModus();
  toon();
  $("form").addEventListener("submit", verstuur);
  $("naam").focus();
})();
