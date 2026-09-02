## Why

Notificaties op de telefoon ontbreken: Mark krijgt review-verdicts of "PR wacht op
je merge" niet binnen als de app dicht is. Een geïnstalleerde PWA kan dat alleen
via Web Push (een push-service levert de melding, ook met de app gesloten).

## What Changes

- **VAPID-sleutels** (public in de VM-env, private SOPS-versleuteld).
- **VM-backend (stdlib)**: `/api/push/vapid` (serveert de public key) +
  `/api/push/subscribe` (bewaart de subscription in `chat/push_subs.json`, dedup).
- **Service worker**: `push`- en `notificationclick`-handlers (toon melding, open
  de app).
- **Frontend**: een 🔔-knop die permissie vraagt, abonneert en de subscription post.
- **Sender op agent-lxc**: `orchestrator/push-notify.py` (uv + pywebpush) leest de
  subs van de VM en verstuurt met de VAPID-private. De VM-backend blijft
  dependency-loos; de crypto zit waar de events al leven (agent-lxc).
