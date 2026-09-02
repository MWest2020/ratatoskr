# Tasks: add-web-push

- [x] 1.1 VAPID-sleutels gegenereerd; public in VM-env, private+subject in SOPS.
- [x] 1.2 chat/push.py (subscription-opslag, stdlib, vormvalidatie + FIFO-cap +
      0600) + /api/push/vapid + /api/push/subscribe in server.py.
- [x] 1.3 sw.js: push + notificationclick (focus + navigate naar url).
- [x] 1.4 app-ui.js: 🔔-knop + stil zelfherstel van de subscription bij load.
- [x] 1.5 orchestrator/push-notify.py: sender op agent-lxc (pywebpush, VAPID uit
      SOPS, subs van de VM; ssh-fout ≠ succes; 404/410 → prune).
- [x] 1.6 notify/buzz-notify.sh: verdict (run-end) + escalatie vuren een push
      (best-effort, achtergrond, BUZZ_PUSH=1) + spec-delta run-notifications +
      notify/README.md-vereisten.
- [x] 1.7 Plumbing live-gesmoked op de VM: /api/push/vapid geeft de key,
      /api/push/subscribe schrijft push_subs.json (0600), sender ondertekent VAPID.
- [ ] 1.8 Eind-tot-eind op een echt toestel: Mark meldt aan via 🔔 en ontvangt een
      testpush met de app gesloten. (Vereist een fysiek toestel; niet in-repo te
      verifiëren — buiten de PASS-poort van deze change.)
