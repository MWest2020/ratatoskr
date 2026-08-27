# chat — mobiele boomhuis-interface

Slack/Telegram-achtige webchat op de relay-VM: lezen én posten in de kanalen,
vanaf de telefoonbrowser over het tailnet. `server.py` (stdlib) praat via
`buzz-cli`; de nsec (identiteit `mark`) zit in de procesomgeving, nóóit in de
browser. Tailnet-only.

## Draaien (op de relay-VM)
    BUZZ_PRIVATE_KEY=<mark-nsec, sops -d> \
    BUZZ_RELAY_URL=ws://192.168.178.60:3000 \
    PORT=8090 python3 server.py

Open op de telefoon (Tailscale aan): http://192.168.178.60:8090/

## Nog te doen (hardening)
- Als systemd-service in de homelab-repo (nu nohup; overleeft geen reboot).
- nsec bij start uit SOPS halen i.p.v. env op de commandline.
- Wanneer de chat-native agents live zijn (fase 2), verschijnen ze vanzelf in
  dezelfde kanalen — dan wordt dit de plek waar je ze aanstuurt.
