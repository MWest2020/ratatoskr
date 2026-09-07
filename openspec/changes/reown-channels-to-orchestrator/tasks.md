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
- [x] 1.2b Overdracht gedraaid door Mark (2026-09-07): #statistics,
      #technical_debt, #red-team, #wordsworth en #netnl hebben de orchestrator
      als mede-eigenaar. De relay staat meerdere eigenaren toe; het script meldde
      eerst ten onrechte "mislukt" omdat het de eerste eigenaar uit de lijst las
      in plaats van te kijken óf de orchestrator erbij stond — gecorrigeerd.
- [ ] 1.2c **Deploy**: `BUZZ_ORCHESTRATOR_KEY` in `/opt/buzz-build/chat/chat.env`
      (root:600) + `systemctl restart boomhuis-chat`. Tot dan geeft kanaalbeheer
      in de web-app 503 met een leesbare melding.
- [x] 1.3 `set-channel-descriptions.py` zet met de orchestrator-sleutel de
      beschrijving op **alle vijftien** kanalen (exit 0). Dat is het bewijs dat
      kanaalbeheer de mens-sleutel niet meer nodig heeft.
- [x] 1.4 Tests: `python3 -m unittest test_admin_key test_auth` groen (6).
- [x] 1.5 `openspec validate --strict` groen.
