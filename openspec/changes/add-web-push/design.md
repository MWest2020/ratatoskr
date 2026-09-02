# Design: add-web-push

## 1. Versturen vanaf agent-lxc, niet vanaf de VM

**Keuze:** de VM bewaart subscriptions + serveert de VAPID-public; het versturen
(pywebpush) gebeurt vanaf agent-lxc.

**Verworpen:** de send op de VM-backend. Web Push vereist payload-encryptie +
VAPID-signing (pywebpush); de VM-backend is bewust stdlib-only en heeft geen pip.
De notificatie-events (review-verdicts) leven bovendien al op agent-lxc (daar
dispatch ik + lees ik verdicts), dus de sender hoort daar. Dependency-scheiding
blijft schoon.

## 2. VAPID-public in env, private in SOPS

**Keuze:** public key in de VM-`chat.env` (het is publiek; de frontend haalt 'm via
`/api/push/vapid`); private + subject SOPS-versleuteld in `secrets/vapid.yaml` (de
sender op agent-lxc decrypt 'm).

**Verworpen:** private in de VM-env. De VM heeft de private niet nodig (verstuurt
niet) en env op de host is zwakker dan SOPS+age in git.
