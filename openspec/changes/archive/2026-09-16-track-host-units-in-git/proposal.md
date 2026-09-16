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

## Wat het onderzoek opleverde, en waarom de change omdraait

Bij het uitvoeren is eerst gemeten of die timer zijn werk doet. Dat deed hij
niet: **82 mislukkingen in veertien dagen, nul keer geslaagd.** Eerst host key
verification tegen cp-01, daarna `Permission denied (publickey)`. De timer stond
al die tijd op `active (waiting)`.

Daarna is nagekeken wat habitat werkelijk doet. `dispatch/dispatch.sh` schrijft
`claude-credentials` al bij **elke dispatch** vanaf de credentials van de
orchestrator-host — dát is het mechanisme uit taak 4.2. De Job-template heeft
bovendien zowel `claude-credentials` als `claude-oauth-token` op `optional:
true`. En in namespace `agents` bestond `claude-credentials` helemaal niet meer;
wel `claude-oauth-token`.

Dus: de workaround was kapot, overbodig, én in strijd met het besluit dat hij
moest ondersteunen — taak 4.2 zegt "één schrijver, workers verversen nooit zelf,
vanwege een rotatie-race", en een vier-uurlijkse timer op deze host ís die
tweede schrijver.

**Een kapotte, overbodige, verboden workaround hoort niet in git.** Hij hoort
weg. Dat is op 2026-09-16 gedaan, met kopie en terugzet-instructie in
`~/archief/claude-secret-refresh-2026-09-16/`.

## What Changes

- **`scripts/check_timers.py`** — welke van onze timers faalde bij zijn laatste
  run. Dit is de gate die ontbrak: `check_units.py` vergelijkt geïnstalleerd met
  git en zegt niets over slagen. Aangesloten op `verify.sh`.
- **`scripts/check_units.py`** krijgt alsnog de omgekeerde richting: een unit die
  alleen op de host staat is per constructie onzichtbaar voor de huidige gate.
  Dat blijft waar, ook nu de aanleiding is opgeruimd.
- Een **uitzonderingslijst met reden en herkomst-repo**, niet een kale allowlist.
  `zettelkast-daily.{service,timer}` hoort bij MWest2020/zettelkast.

## Wat hier NIET meer in zit

- De units en het script in git zetten. Dat was het oorspronkelijke voorstel en
  het is achterhaald: je zet geen dode code in de waarheid.
- Het herontwerp van de credential-rotatie. Sync-at-dispatch doet het al.

## Impact

- `orchestrator/systemd/`, `scripts/check_units.py`, `verify.sh`.
- Gate vóór apply: **security-review van unit-files én script** — geen
  credential, token of sleutelpad letterlijk in git. Uitgevoerd op 2026-09-16,
  uitkomst in `tasks.md`.
