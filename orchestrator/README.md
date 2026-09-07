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
