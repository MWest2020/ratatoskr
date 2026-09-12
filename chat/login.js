// SPDX-License-Identifier: EUPL-1.2
// One page, three situations: logging in, creating the first person (setup), and
// using an invitation. They differ only in which endpoint is called and which
// fields you see — a separate page per case gives you the same form three times.

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
  // A fresh installation without a setup link in the URL: then the only sensible
  // screen is "create the owner", with the old shared token as the key.
  try{
    const r = await fetch("/api/status");
    const s = await r.json();
    if ((s.personen || 0) === 0){ mode = "setup"; $("tokenField").hidden = false; }
  }catch(e){ /* leave the login screen as it is */ }
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
      // Name and password were right; now the second factor. The field only
      // appears here, so anyone without a second factor never sees one.
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
