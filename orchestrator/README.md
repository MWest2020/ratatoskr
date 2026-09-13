# orchestrator/bridge — doel→dispatch-brug (deel B)

Poortwachter-model: **niets dispatcht autonoom.** Alleen een expliciet bericht
van Mark in #bouw — `!dispatch <rol> <change> <repo>` — passeert de poort. De
brug neemt dan het laatste `bouwer`-plan uit de thread als taak/context en
bereidt een habitat-dispatch voor met `HABITAT_TASK_REF` (git-pad in de doelrepo,
zie habitat `amend-worker-task-ref`).

De cage-fire blijft onder Marks hand:
- `BRIDGE_LIVE` niet gezet → de brug POST alleen het exacte dispatch-commando
  terug; Mark draait het zelf op de kubectl-host (gesuperviseerd).
- `BRIDGE_LIVE=1` → de brug draait `dispatch.sh` zelf (pas inschakelen als je de
  brug vertrouwt).

## Draaien (orchestrator-host, buiten de kooi)
    BUZZ_PRIVATE_KEY=<orchestrator-nsec, sops -d> \
    BUZZ_RELAY_URL=ws://192.168.178.60:3000 \
    DISPATCH_SH=/pad/naar/habitat/dispatch/dispatch.sh \
    WORKER_IMAGE=ghcr.io/mwest2020/habitat-worker:<nieuwe-sha> \
    python3 orchestrator/bridge.py

## Voor een échte live run nog nodig
- De worker-image met HABITAT_TASK_REF-support (CI bouwt 'm na de
  amend-worker-task-ref-merge) pinnen als WORKER_IMAGE.
- Een host met kubectl-toegang tot de agents-namespace + git-write naar de
  doelrepo.
- De eerste live dispatch gesuperviseerd: BRIDGE_LIVE=1 en samen kijken.

Deel A (findings-terug) is een aparte, uitgaande stap (geen kooi-amendement) —
zie de change tasks.

## add-member.py — pubkey als kanaallid

    python3 orchestrator/add-member.py --chan escalatie --name odin-worker

Lost kanaal en identiteit op uit `channels.yml` / `identities.yml`, zodat er geen
UUID of pubkey op de commandline hoeft (die breken in een terminal over meerdere
regels en falen dan stil-verkeerd). `--all-channels` voegt in één keer overal toe,
idempotent — "al lid" is geen fout.

Tekent standaard als **orchestrator**, conform `reown-channels-to-orchestrator`.
Is een kanaal nog mens-owned, dan `IDENT=mark` ervoor tot `reown-channels.py`
gedraaid heeft.

## push-notify.py — een melding naar de telefoon

    uv run orchestrator/push-notify.py --title "PR #7" --body "verdict: FAIL" --url /

Leest de abonnementen van de VM via de gepinde helper (`boomhuis-push-subs read`)
en verstuurt met de VAPID-sleutel uit SOPS. Zonder abonnees zegt hij dat en stopt.

**De verzendkant testen zonder telefoon:**

    cd orchestrator && uv run --with pywebpush --with pyyaml --with cryptography \
      --with http-ece python -m unittest test_push_send -v

Die test speelt zelf voor pushdienst: hij maakt een abonnement zoals een browser
dat doet, vangt de POST op localhost en ontsleutelt de inhoud. Hij bewijst alles
wat aan ónze kant fout kan gaan — SOPS, de JWT-ondertekening, de versleuteling,
en de `Urgency`/`TTL`-headers die bepalen wánneer een toestel de melding ziet.
Slaat zichzelf over als SOPS of de age-sleutel ontbreekt, want `verify.sh` moet
offline groen zijn; hij draait dus alleen als je hem expliciet zo aanroept.

Blijft er daarna nog "geen meldingen" over, dan zit het in de browser-permissie
op het toestel — zie `chat/app-push.js` en `chat/e2e/push-states.js`.
