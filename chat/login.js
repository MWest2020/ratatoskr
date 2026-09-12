// SPDX-License-Identifier: EUPL-1.2
// Eén pagina, drie situaties: inloggen, de eerste persoon aanmaken (setup), en
// een uitnodiging gebruiken. Ze verschillen alleen in welk endpoint er
// aangeroepen wordt en welke velden je ziet — een aparte pagina per geval
// levert drie keer hetzelfde formulier op.

const params = new URLSearchParams(location.search);
const setupToken = params.get("setup") || "";
const invite = params.get("uitnodiging") || "";
const back = params.get("terug") || "/";

const $ = (id) => document.getElementById(id);
const message = (text) => { $("message").textContent = text; $("message").hidden = !text; };

let mode = "inloggen";
if (invite) mode = "uitnodiging";
else if (setupToken) mode = "setup";

async function determineMode(){
  if (mode !== "inloggen") return;
  // Verse installatie zonder setup-link in de URL: dan is het enige zinnige
  // scherm "maak de eigenaar aan", met het oude gedeelde token als sleutel.
  try{
    const r = await fetch("/api/status");
    const s = await r.json();
    if ((s.personen || 0) === 0){ mode = "setup"; $("tokenField").hidden = false; }
  }catch(e){ /* laat het inlogscherm staan */ }
}

function render(){
  const titles = {
    inloggen: ["Inloggen", "Ratatoskr is alleen voor mensen met een account."],
    setup: ["Eerste account", "Dit boomhuis heeft nog niemand. Maak de eigenaar aan."],
    uitnodiging: ["Welkom", "Kies een naam en een wachtwoord van minstens 12 tekens."],
  };
  const [t, u] = titles[mode];
  $("title").textContent = t;
  $("intro").textContent = u;
  $("submit").textContent = mode === "inloggen" ? "Inloggen" : "Account maken";
  $("name").autocomplete = mode === "inloggen" ? "username" : "off";
  $("password").autocomplete = mode === "inloggen" ? "current-password" : "new-password";
}

async function submit(e){
  e.preventDefault();
  message("");
  $("submit").disabled = true;
  const body = { naam: $("name").value, wachtwoord: $("password").value };
  let path = "/api/login";
  if (mode === "setup"){ path = "/api/setup"; body.token = setupToken || $("token").value; }
  if (mode === "uitnodiging"){ path = "/api/uitnodiging/gebruik"; body.token = invite; }
  if (!$("codeField").hidden) body.code = $("code").value;

  try{
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const d = await r.json().catch(() => ({}));
    if (r.ok){ location.replace(back.startsWith("/") ? back : "/"); return; }
    if (d.totp){
      // Naam en wachtwoord klopten; nu de tweede factor. Het veld verschijnt
      // pas hier, zodat wie geen tweede factor heeft er ook geen ziet.
      $("codeField").hidden = false;
      $("code").focus();
      message(d.error === "code nodig" ? "Vul de code uit je app in." : "Die code klopt niet.");
    } else if (r.status === 429){
      message("Te veel pogingen. Probeer het over " + (d.wacht || 60) + " seconden opnieuw.");
    } else {
      message(d.error || "Er ging iets mis.");
    }
  }catch(err){
    message("Geen verbinding met het boomhuis — staat Tailscale aan?");
  }finally{
    $("submit").disabled = false;
  }
}

(async function start(){
  await determineMode();
  render();
  $("form").addEventListener("submit", submit);
  $("name").focus();
})();
