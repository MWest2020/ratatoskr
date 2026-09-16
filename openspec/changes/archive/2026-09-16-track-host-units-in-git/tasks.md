## 1. Gate vóór alles

- [x] 1.1 Security-review van `refresh-claude-secret.sh` (2026-09-16): geen
      letterlijk secret, token of sleutel. Paden gaan via `$HOME` en een
      ssh-alias (`cp-01`); `--kubeconfig /etc/kubernetes/admin.conf` is een pad
      op de doelnode, geen geheim. Het script *verwerkt* credentials, het
      *bevat* ze niet. Gate: open.
- [x] 1.2 Unit-files nagekeken: `claude-secret-refresh.service` bevat alleen een
      omschrijving en `ExecStart`, de timer alleen een schema. Geen geheim.

## 2. Meten voordat je iets in git zet

- [x] 2.1 Doet de timer zijn werk? Nee: 82 mislukkingen in veertien dagen, nul
      keer geslaagd. Eerst host key verification tegen cp-01, daarna
      `Permission denied (publickey)` voor `ubuntu@192.168.178.201`.
- [x] 2.2 Wat doet habitat werkelijk? `dispatch/dispatch.sh` schrijft
      `claude-credentials` bij elke dispatch; de Job-template heeft beide
      secrets op `optional: true`; in namespace `agents` bestond
      `claude-credentials` niet, wel `claude-oauth-token`.
- [x] 2.3 Conclusie: kapot, overbodig én een tweede schrijver op een secret waar
      taak 4.2 er één voorschrijft. Opgeruimd op 2026-09-16, met kopie en
      terugzet-instructie in `~/archief/claude-secret-refresh-2026-09-16/`.

## 3. De gate die ontbrak

- [x] 3.1 `scripts/check_timers.py`: welke van onze timers faalde bij zijn
      laatste run. Aangesloten op `verify.sh`.
- [x] 3.2 Tests, waaronder: een systemd-eigen timer telt niet mee (anders is de
      gate ruis), en `?` telt als fout — niet kunnen vaststellen is geen bewijs
      dat het goed ging.
- [x] 3.3 `scripts/check_units.py`: de omgekeerde richting (host-unit zonder
      repo-tegenhanger).
- [x] 3.4 Uitzonderingslijst met reden en herkomst-repo.
- [x] 3.5 Nameten dat 3.3 faalt zonder de wijziging.

## 4. De sluitvoorwaarde is al gehaald

- [x] 4.1 De toetsdatum van 2026-12-14 is niet meer nodig. De sluitvoorwaarde
      luidde: sync-at-dispatch levert verse credentials terwijl de timer
      gestopt is. Die timer stond veertien dagen effectief stil en er viel niets
      om — en `dispatch.sh` doet de sync aantoonbaar zelf.

## 5. Groen

- [x] 5.1 `bash verify.sh` groen, inclusief de nieuwe tests.
- [x] 5.2 Docs-gate groen (deze change raakt `scripts/`, dus `docs/` beweegt mee).
