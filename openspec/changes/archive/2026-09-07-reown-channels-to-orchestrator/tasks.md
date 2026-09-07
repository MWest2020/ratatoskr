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
- [x] 1.2c **Deploy** (2026-09-07): `BUZZ_ORCHESTRATOR_KEY` staat in
      `/opt/buzz-build/chat/chat.env` (root:root 600, back-up ernaast) en zit in
      de procesomgeving van `boomhuis-chat` als `nsec1…`. Daarbij bleek de
      backend op de VM nog de oude te zijn — `server.py`, `actions.py` en
      `buzzcli.py` weken af van main, dus de code die de sleutel gebruikt draaide
      er niet. Alsnog uitgerold en herstart.
- [x] 1.6 **End-to-end op de draaiende code** (zonder de web-app, die een
      apparaat-token vraagt): `actions.create_channel()` met de uitgerolde code en
      de echte omgeving geeft 200, en het nieuwe kanaal is
      `orchestrator`-owned met `odin` als bot erin. Verwijderen lukt eveneens met
      de orchestrator-sleutel. Beide testkanalen opgeruimd.
- [x] 1.3 `set-channel-descriptions.py` zet met de orchestrator-sleutel de
      beschrijving op **alle vijftien** kanalen (exit 0). Dat is het bewijs dat
      kanaalbeheer de mens-sleutel niet meer nodig heeft.
- [x] 1.4 Tests: `python3 -m unittest test_admin_key test_auth` groen (6).
- [x] 1.5 `openspec validate --strict` groen.
