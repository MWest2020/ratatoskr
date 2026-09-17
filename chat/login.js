// SPDX-License-Identifier: MIT
// One page, three situations: logging in, creating the first person (setup), and
// using an invitation. They differ only in which endpoint is called and which
// fields you see — a separate page per case gives you the same form three times.

const params = new URLSearchParams(location.search);
const setupToken = params.get("setup") || "";
const invite = params.get("uitnodiging") || "";
const back = params.get("terug") || "/";

const $ = (id) => document.getElementById(id);
const message = (text) => { $("message").textContent = text; $("message").hidden = !text; };

let mode = "signin";
if (invite) mode = "invite";
else if (setupToken) mode = "setup";

async function determineMode(){
  if (mode !== "signin") return;
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
    signin: ["Sign in", "Ratatoskr is only for people with an account."],
    setup: ["First account", "This boomhuis has nobody yet. Create the owner."],
    invite: ["Welcome", "Pick a name and a password of at least 12 characters."],
  };
  const [t, u] = titles[mode];
  $("title").textContent = t;
  $("intro").textContent = u;
  $("submit").textContent = mode === "signin" ? "Sign in" : "Create account";
  $("name").autocomplete = mode === "signin" ? "username" : "off";
  $("password").autocomplete = mode === "signin" ? "current-password" : "new-password";
}

async function submit(e){
  e.preventDefault();
  message("");
  $("submit").disabled = true;
  const body = { naam: $("name").value, wachtwoord: $("password").value };
  let path = "/api/login";
  if (mode === "setup"){ path = "/api/setup"; body.token = setupToken || $("token").value; }
  if (mode === "invite"){ path = "/api/uitnodiging/gebruik"; body.token = invite; }
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
      message(d.error === "code required" ? "Enter the code from your app." : "That code is wrong.");
    } else if (r.status === 429){
      message("Too many attempts. Try again in " + (d.wacht || 60) + " seconds.");
    } else {
      message(d.error || "Something went wrong.");
    }
  }catch(err){
    message("No connection to the boomhuis — is Tailscale on?");
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
