## 1. Gate vóór alles

- [x] 1.1 Security-review van `refresh-claude-secret.sh` (2026-09-16): geen
      letterlijk secret, token of sleutel. Paden gaan via `$HOME` en een
      ssh-alias (`cp-01`); `--kubeconfig /etc/kubernetes/admin.conf` is een pad
      op de doelnode, geen geheim. Het script *verwerkt* credentials, het
      *bevat* ze niet. Gate: open.
- [x] 1.2 Unit-files nagekeken: `claude-secret-refresh.service` bevat alleen een
      omschrijving en `ExecStart`, de timer alleen een schema. Geen geheim.

## 2. In git

- [ ] 2.1 `orchestrator/systemd/claude-secret-refresh.{service,timer}`,
      letterlijk overgenomen van de host.
- [ ] 2.2 `orchestrator/systemd/refresh-claude-secret.sh`, letterlijk, met de
      uitleg waarom hij hier staat en niet in `scripts/` (hij hoort bij de unit
      en wordt door `%h` aangeroepen, niet door een mens).
- [ ] 2.3 De host laat verwijzen naar de git-versie in plaats van een losse
      kopie in de home-map, zodat `check_units.py` er iets over kan zeggen.

## 3. De gate beide kanten op

- [ ] 3.1 `scripts/check_units.py`: elke unit in `~/.config/systemd/user` die op
      `ratatoskr-*` of `claude-*` lijkt en geen tegenhanger in de repo heeft →
      melding.
- [ ] 3.2 Uitzonderingslijst met reden en herkomst-repo; `zettelkast-daily` als
      eerste en voorlopig enige.
- [ ] 3.3 Tests: een host-unit zonder repo-tegenhanger wordt gemeld; een unit op
      de uitzonderingslijst niet; een uitzondering zónder reden is een fout in
      de lijst zelf.
- [ ] 3.4 Nameten dat de test faalt zonder de wijziging.

## 4. De workaround een einde geven

- [ ] 4.1 In `tasks.md` vastleggen — **sluitvoorwaarde**: een dispatch waarvan
      het token midden in de Job verloopt, krijgt verse credentials terwijl
      `claude-secret-refresh.timer` gestopt is. Gemeten, niet beredeneerd.
- [ ] 4.2 **Toetsdatum 2026-12-14.** Haalt de meting het niet, dan is de uitkomst
      geen verlenging maar een expliciet besluit dat de timer blijft — mét wie de
      tweede-schrijver-race dan bewaakt. Een workaround mag permanent worden; hij
      mag alleen niet permanent worden zonder dat iemand dat koos.

## 5. Groen

- [ ] 5.1 `bash verify.sh` groen, inclusief de nieuwe tests.
- [ ] 5.2 Docs-gate groen (deze change raakt `scripts/`, dus `docs/` beweegt mee).
