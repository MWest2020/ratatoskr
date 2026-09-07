# chat — mobiele boomhuis-interface

Slack/Telegram-achtige webchat op de relay-VM: lezen én posten in de kanalen,
vanaf de telefoonbrowser over het tailnet. De backend is opgesplitst (elk bestand
≤200 regels): `buzzcli.py` (stdlib) is de relay-datalaag, `roster.py` de
identiteits-/ledenlogica, `actions.py` de send/add/create-acties, en `server.py`
doet alleen de HTTP-routing + serveert de PWA-shell (`index.html` +
`app.css`/`app.js`/`app-auth.js`/`app-modal.js`/`app-repos.js`/`app-ui.js`/`app-push.js`).
De nsec (identiteit `mark`) zit in de procesomgeving, nóóit in de browser.
Tailnet-only.

**Volgorde van de scripts is inhoudelijk.** `app-modal.js` levert `el()`/`add()`
en moet vóór `app.js`; `app-repos.js` moet vóór `app-ui.js`, want die bindt de
Repos-knop bij het laden (andersom: `openRepos is not defined`).

## Alles van buiten wordt tekst

`el(tag, class, tekst)` zet tekst via `textContent`, nooit via `innerHTML`. Dat is
geen stijlkeuze. De Repos-lade toont repo-beschrijvingen, PR-titels, branchnamen,
bestandsnamen en de PR-URL, en die kan **iedereen** zetten door een PR te openen
op een publieke repo. Tot 2026-09-07 ging dat via `innerHTML`; gemeten voerde een
payload in een PR-titel script uit in de PWA — waar het apparaat-token in
`localStorage` staat — en werd `javascript:…` een klikbare link. De regressietest
staat in `e2e/xss.js`.

## Testen

    bash ../verify.sh       # unittests, offline
    bash e2e/api.sh         # routes + auth-gate tegen de VM
    node e2e/ui.js          # browser-kant tegen de VM
    node e2e/xss.js         # regressietest op de GitHub-rendering

## Draaien (op de relay-VM)

Draait als systemd-unit `boomhuis-chat.service` (unit-file: homelab-repo
`ansible/files/boomhuis-chat.service`). De nsec komt uit
`/opt/buzz-build/chat/chat.env` (root:600) via `EnvironmentFile` — nooit op de
commandline (ps-zichtbaar) en nooit in git; de SOPS-bron is
`secrets/identities.yaml` in deze repo. Beheer:

    sudo systemctl status|restart boomhuis-chat

Open op de telefoon (Tailscale aan): https://boomhuis-relay.tail8f7877.ts.net/
(HTTPS via tailscale serve — een secure context, nodig voor de service worker).

## Schrijf-token (BOOMHUIS_APP_TOKEN)

Tweede laag onder de netwerklaag: staat `BOOMHUIS_APP_TOKEN` in `chat.env`, dan
eist elke POST (send, kanaal maken/verwijderen, agent toevoegen,
push-registratie) een gelijke `X-App-Token`; anders 401, vóór er ook maar iets
richting de relay gaat. Leeg of afwezig = uit, gedrag ongewijzigd. Lezen blijft
altijd open — meelezen op het tailnet is geen impersonatie, schrijven wel (alles
komt aan als `mark`).

De PWA vraagt het token bij de eerste 401 en bewaart het in `localStorage` van
dat apparaat; de server zet het nooit in de pagina (wie de pagina kan ophalen,
zou het anders kunnen lezen). Vergelijking is constant-time; het token staat in
geen enkel log of antwoord. Agents raakt dit niet: `ping.sh` en de chat-native
agents tekenen zelf tegen de relay en gebruiken deze HTTP-API niet.

Token wijzigen: waarde in `chat.env` aanpassen, `sudo systemctl restart
boomhuis-chat`, en op elk apparaat één keer opnieuw invoeren.

## Kanaalbeheer (BUZZ_ORCHESTRATOR_KEY)

Kanalen maken, verwijderen en leden toevoegen tekent met de **orchestrator**-nsec
uit `BUZZ_ORCHESTRATOR_KEY` in `chat.env`, niet met de `mark`-nsec waarmee de
backend berichten stuurt. Zo zijn nieuwe kanalen agent-owned en kan
`orchestrator/set-channel-descriptions.py` ze bijwerken zonder mens-sleutel.

Staat de variabele niet, dan geeft elk beheerpad **503** met
"kanaalbeheer staat uit" — het valt bewust niet terug op marks sleutel (dat zou
een stil auditgat zijn). Berichten sturen blijft ongemoeid.

Bestaande mens-owned kanalen draag je eenmalig over met
`orchestrator/reown-channels.py` (idempotent, `--dry-run` beschikbaar).

## Web Push (telefoon-notificaties)

Verdicts en escalaties komen als push op de telefoon, ook met de app dicht.
De crypto (VAPID-signing) zit bewust NIET op deze backend maar op agent-lxc
(`orchestrator/push-notify.py`, uv + pywebpush); deze backend blijft stdlib-loos.

Wat waar staat en terug moet na een redeploy of host-herstel:

- **`VAPID_PUBLIC`** — in `chat.env` (publiek; de frontend haalt 'm via
  `/api/push/vapid`). Zonder deze waarde blijft push stil uit.
- **`PUSH_SUBS_PATH=/var/lib/boomhuis/push_subs.json`** — in `chat.env`. State
  BUITEN de checkout (`/opt/buzz-build`), anders wist een redeploy de abonnees.
  De backend (root) schrijft 'm 0600; maak de dir eenmalig: `sudo mkdir -p
  /var/lib/boomhuis`.
- **`secrets/vapid.yaml`** (deze repo, SOPS+age) — VAPID-private + subject. Alleen
  de sender op agent-lxc decrypt 'm; de VM heeft de private nooit nodig.

Versturen (vanaf agent-lxc): `uv run orchestrator/push-notify.py --title … --url /
--body "…"` (met `SOPS_AGE_KEY_FILE` gezet). De sender leest de subs via `sudo` op
de VM en ruimt verlopen subscriptions (404/410) op. Automatisch afgevuurd door
`notify/buzz-notify.sh` (run-end + escalate) als `BUZZ_PUSH=1`.

Host-config die de sender nodig heeft (naast de env-waarden hierboven):

- **VM-helper + één vastgepinde sudoers-regel.** De backend schrijft `push_subs.json`
  als root 0600; de sender sshet als `ubuntu` en kan dat niet lezen zonder sudo.
  I.p.v. `sudo cat`/`sudo python3` (feitelijk een root-shell) draait de sender één
  vastgepinde helper. Deploy 'm uit deze repo:
  `sudo install -m0755 orchestrator/vm/boomhuis-push-subs /usr/local/bin/boomhuis-push-subs`.
  Sudoers (`/etc/sudoers.d/boomhuis-push`, least privilege — precies dit pad):
  `ubuntu ALL=(root) NOPASSWD: /usr/local/bin/boomhuis-push-subs`. De helper maakt
  ook `/var/lib/boomhuis` aan als 'ie ontbreekt.
- **ssh-alias `buzz-relay`** in `~/.ssh/config` op agent-lxc (BatchMode, key-based)
  → de VM `192.168.178.60`.

## Nog te doen (hardening)
- Wanneer de chat-native agents live zijn (fase 2), verschijnen ze vanzelf in
  dezelfde kanalen — dan wordt dit de plek waar je ze aanstuurt.
