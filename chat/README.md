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

## Nog te doen (hardening)
- Wanneer de chat-native agents live zijn (fase 2), verschijnen ze vanzelf in
  dezelfde kanalen — dan wordt dit de plek waar je ze aanstuurt.
