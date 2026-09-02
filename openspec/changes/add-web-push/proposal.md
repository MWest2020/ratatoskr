## Why

Notificaties op de telefoon ontbreken: Mark krijgt review-verdicts of "PR wacht op
je merge" niet binnen als de app dicht is. Een geïnstalleerde PWA kan dat alleen
via Web Push (een push-service levert de melding, ook met de app gesloten).

## What Changes

- **VAPID-sleutels** (public in de VM-env, private SOPS-versleuteld).
- **VM-backend (stdlib)**: `/api/push/vapid` (serveert de public key) +
  `/api/push/subscribe` (vormvalidatie + dedup + FIFO-cap, 0600, state buiten de
  checkout via `PUSH_SUBS_PATH`).
- **Service worker**: `push`- en `notificationclick`-handlers (toon melding, focus
  + navigeer naar de url).
- **Frontend**: een 🔔-knop die permissie vraagt en abonneert; bij een reeds
  verleende permissie borgt de app de subscription stil bij elke load (zelfherstel).
- **Sender op agent-lxc**: `orchestrator/push-notify.py` (uv + pywebpush) leest de
  subs van de VM en verstuurt met de VAPID-private; een gefaalde ssh-hop telt niet
  als succes en verlopen subs (404/410) worden opgeruimd. De VM-backend blijft
  dependency-loos; de crypto zit waar de events al leven (agent-lxc).
- **Bedrading**: `notify/buzz-notify.sh` vuurt bij een verdict (run-end) en een
  escalatie een push af (best-effort, `BUZZ_PUSH=1`), zodat de telefoon rinkelt.
