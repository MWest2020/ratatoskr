# Change: track-host-units-in-git

## Why

`claude-secret-refresh.{service,timer}` staat op deze host in
`~/.config/systemd/user/` en **niet in git**. De timer draait elke vier uur, de
omschrijving zegt "habitat taak 4.2 workaround", en als hij omvalt zie je dat
nergens — tot habitat-workers omvallen op verlopen credentials.

Maar dat is het symptoom. Het echte gat zit in de gate zelf: `check_units.py`
kijkt maar één kant op. Voor elke unit **in de repo** controleert hij de host. Een
unit die alleen op de host staat en nooit in de repo, is per constructie
onzichtbaar. De gate meet precies de verzameling waar het gat niet in zit.

Dat is dezelfde vorm die deze week vijf keer terugkwam: de regel bestaat, alleen
niet op het pad dat gelopen wordt.

**Wat NIET waar bleek.** De eerste lezing was dat ook `ratatoskr-live.{service,
timer}` buiten git stonden. Onjuist: die staan in `orchestrator/systemd/` en
worden al gedekt. En de tweede lezing — dat `claude-secret-refresh` op de
listener-VM draait — was óók onjuist, en op een leerzame manier: er is gekeken
met `systemctl cat` in de **system**-scope terwijl het **user**-units zijn. De
verkeerde verzameling meten en dan "staat er niet" concluderen is letterlijk de
fout die deze change moet afsluiten.

## What Changes

- `claude-secret-refresh.{service,timer}` in git, plus
  **`refresh-claude-secret.sh`**. Een unit zonder dat script is decoratie: het
  script is waar het gedrag zit — het leest `~/.claude/.credentials.json`, ssh't
  naar `cp-01` en herschrijft daar het secret in namespace `agents`.
- `scripts/check_units.py` krijgt de omgekeerde richting: elke unit in
  `~/.config/systemd/user` die op `ratatoskr-*` of `claude-*` lijkt en geen
  tegenhanger in de repo heeft, is een melding.
- Een **uitzonderingslijst met reden en herkomst-repo**, niet een kale
  allowlist. `zettelkast-daily.{service,timer}` staat hier geïnstalleerd en hoort
  bij MWest2020/zettelkast. Een uitzondering die zegt waaróm is toezicht; een
  uitzondering zonder reden is een blinde vlek met een net pak aan.
- Sluitvoorwaarde en toetsdatum voor de workaround in `tasks.md`.

## Wat hier NIET in zit

- `/usr/bin/python3` en `ssh jumpy kubectl` in `ratatoskr-live`. Die staan al zo
  in de git-versie, dus het zijn ontwerpvragen, geen drift.
- Het herontwerp van de credential-rotatie zelf (habitat `add-dispatch` 4.2).
  Alleen de sluitvoorwaarde wordt hier vastgelegd.

## Impact

- `orchestrator/systemd/`, `scripts/check_units.py`, `verify.sh`.
- Gate vóór apply: **security-review van unit-files én script** — geen
  credential, token of sleutelpad letterlijk in git. Uitgevoerd op 2026-09-16,
  uitkomst in `tasks.md`.
