# Tasks: reown-channels-to-orchestrator

- [x] 1.1 Kanaalbeheer (maken, verwijderen, lid toevoegen) tekent als
      orchestrator via `buzz_admin` (`BUZZ_ORCHESTRATOR_KEY`); marks sleutel
      wordt nergens meer voor beheer gebruikt. Fail-closed: zonder sleutel 503,
      geen stille terugval.
- [x] 1.2a Overdrachtsmechanisme uitgezocht: de relay ondersteunt
      `channels add-member --role owner`, dus her-eigenaren kán zonder
      recreëren. Script `orchestrator/reown-channels.py` (idempotent, `--dry-run`)
      doet precies die ene rolwijziging met marks sleutel — de enige plek waar
      die sleutel gebruikt mag worden.
- [ ] 1.2b **Wacht op Mark**: de auto-mode classifier weigert de agent
      kanaal-lidmaatschap/eigenaarschap te wijzigen. Vijf kanalen staan nog op
      `mark`: #statistics, #technical_debt, #red-team, #wordsworth, #netnl.
      Draaien: `SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt python3
      ~/boomhuis/orchestrator/reown-channels.py`
- [ ] 1.2c **Deploy**: `BUZZ_ORCHESTRATOR_KEY` in `/opt/buzz-build/chat/chat.env`
      (root:600) + `systemctl restart boomhuis-chat`. Tot dan geeft kanaalbeheer
      in de web-app 503 met een leesbare melding.
- [ ] 1.3 `set-channel-descriptions.py` zet daarna alle kanalen zonder
      mens-sleutel (nu nog: de vijf hierboven falen).
- [x] 1.4 Tests: `python3 -m unittest test_admin_key test_auth` groen (6).
- [x] 1.5 `openspec validate --strict` groen.
