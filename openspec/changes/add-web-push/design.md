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

## 3. Onbeschermde subscribe-route (tailnet-only, geen per-user auth)

**Keuze:** `/api/push/subscribe` accepteert een subscription zonder auth, maar met
vormvalidatie (`push._valid_sub`: dict met https-endpoint ≤1024 tekens + p256dh/auth)
en een FIFO-cap (`PUSH_MAX_SUBS`, default 50). Het bestand wordt 0600 geschreven.

**Waarom acceptabel:** de hele backend luistert al enkel op het tailnet-IP
(`BIND_HOST=100.x`), dezelfde vertrouwensgrens als `/api/send`. Een subscription is
geen geheim dat lekt maar een push-doel; het ergste dat een tailnet-node kan is
zichzelf aanmelden of de opslag laten groeien — de cap + validatie dekken de groei
en de vorm. Per-user auth bestaat nergens in deze app (bewust: één-mans-tailnet).

**Verworpen:** een gedeeld token op de route. Voegt een geheim toe zonder de
vertrouwensgrens te veranderen (tailnet blijft de poort), en breekt de PWA-install
op Marks telefoon zonder winst.

## 4. Runtime-state buiten de git-checkout

**Keuze:** `push_subs.json` is runtime-state, geen code. Op de VM zet het
deploy-script `PUSH_SUBS_PATH` naar een state-dir buiten `/opt/buzz-build`
(de checkout). De default in `push.py` is enkel een lokale test-fallback en staat
in `.gitignore`. Verlopen subscriptions (404/410) ruimt de sender op.
