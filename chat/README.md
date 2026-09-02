# chat — mobiele boomhuis-interface

Slack/Telegram-achtige webchat op de relay-VM: lezen én posten in de kanalen,
vanaf de telefoonbrowser over het tailnet. `buzzcli.py` (stdlib) praat via
`buzz-cli` met de relay; `server.py` doet de HTTP-routing + serveert de PWA-shell
(`index.html` + `app.css`/`app.js`/`app-ui.js`). De nsec (identiteit `mark`) zit
in de procesomgeving, nóóit in de browser. Tailnet-only.

## Draaien (op de relay-VM)

Draait als systemd-unit `boomhuis-chat.service` (unit-file: homelab-repo
`ansible/files/boomhuis-chat.service`). De nsec komt uit
`/opt/buzz-build/chat/chat.env` (root:600) via `EnvironmentFile` — nooit op de
commandline (ps-zichtbaar) en nooit in git; de SOPS-bron is
`secrets/identities.yaml` in deze repo. Beheer:

    sudo systemctl status|restart boomhuis-chat

Open op de telefoon (Tailscale aan): https://boomhuis-relay.tail8f7877.ts.net/
(HTTPS via tailscale serve — een secure context, nodig voor de service worker).

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

Versturen (vanaf agent-lxc): `IDENT=… uv run orchestrator/push-notify.py --title …
--url / --body "…"`. De sender leest de subs via `sudo` op de VM en ruimt verlopen
subscriptions (404/410) op. Automatisch afgevuurd door `notify/buzz-notify.sh`
(run-end + escalate) als `BUZZ_PUSH=1`.

## Nog te doen (hardening)
- Wanneer de chat-native agents live zijn (fase 2), verschijnen ze vanzelf in
  dezelfde kanalen — dan wordt dit de plek waar je ze aanstuurt.
