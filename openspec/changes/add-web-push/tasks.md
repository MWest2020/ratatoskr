# Tasks: add-web-push

- [x] 1.1 VAPID-sleutels gegenereerd; public in VM-env, private+subject in SOPS.
- [x] 1.2 chat/push.py (subscription-opslag, stdlib) + /api/push/vapid +
      /api/push/subscribe in server.py.
- [x] 1.3 sw.js: push + notificationclick handlers.
- [x] 1.4 app-ui.js: 🔔-knop → permissie + subscribe + POST.
- [x] 1.5 orchestrator/push-notify.py: sender op agent-lxc (pywebpush, VAPID-private
      uit SOPS, subs van de VM).
