# notify

`buzz-notify.sh` post habitat-run-gebeurtenissen naar Ratatoskr via
`buzz-cli`, als de orchestrator-identiteit. Best-effort: een onbereikbare relay
of een fout laat een run nooit falen (exit 0, gemiste post in `notify.log`).

## Vereist op de orchestrator-host
- `buzz` (buzz-cli) op PATH. Bouwen: `cargo build --release -p buzz-cli` in een
  clone van block/buzz (gedaan op de relay-VM in een `rust:1-bookworm`-container;
  binary gekopieerd naar de orchestrator-host).
- `BUZZ_PRIVATE_KEY` = nsec van de orchestrator (uit `secrets/identities.yaml`,
  `sops -d`). `BUZZ_RELAY_URL` default `ws://192.168.178.60:3000`.

### Voor de telefoon-push (run-end + escalate)
Alleen actief met `BUZZ_PUSH=1`; zonder die vlag verandert er niets. Vereist dan
óók op de orchestrator-host:
- `uv` op PATH (draait `orchestrator/push-notify.py` als uv-script).
- `sops` + de age-key (`~/.config/sops/age/keys.txt`) om `secrets/vapid.yaml` te
  decrypten (VAPID-private).
- ssh-alias `buzz-relay` in `~/.ssh/config` (BatchMode) — de sender leest de
  subscriptions van de VM en pruned verlopen endpoints via `sudo` daar.
De push is best-effort en draait op de achtergrond: een ontbrekende sender, lege
uv-cache of onbereikbare push-service houdt een run nooit op. Volledig runbook
(state-pad, VAPID-waarden): `../chat/README.md → "Web Push"`.

## Gebruik
    buzz-notify.sh run-start <rol> <change> <repo> <run_id>      # print root-event-id
    BUZZ_THREAD=<id> buzz-notify.sh run-end <rol> <change> <repo> <run_id> <verdict> <branch> [link]
    buzz-notify.sh escalate <reden> [link]

Kanaal-id's komen uit `../channels.yml`. Aansluiting op habitat: aanroepen
vanuit/naast `dispatch/dispatch.sh` (orchestrator-zijde, buiten de kooi) —
run-start vóór de Job, run-end na de terminale conditie, escalate bij een
FAIL/security-finding. Nog te doen: taak 1.6 (echte habitat-run) en 1.7
(kooi-diff leeg).
