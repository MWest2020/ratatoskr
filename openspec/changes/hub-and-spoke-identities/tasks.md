# Tasks: hub-and-spoke-identities

- [x] 1.1 `coordinator` → `ingetrokken`; `odin` van rol `sessie` naar
      `meta-agent`; listener-run-lijst draait `odin`.
- [x] 1.2 `versum` → `odin-worker` in `identities.yml` en in de SOPS-bundel
      (zelfde sleutelpaar).
- [x] 1.3 `ping.sh`: rol `sessie` + `CHAN=general` → exit 8 met verwijzing.
- [x] 1.4 `buzzcli.NAMES`: `odin` erbij, `coordinator` blijft leesbaar.
- [x] 1.5 Relay-profielnamen van `odin` en `odin-worker` gezet (beide accepted).
- [x] 1.6 Getest: sessie naar #general geweigerd, ingetrokken identiteit
      geweigerd, hub-rol komt door de guard.
- [ ] 1.7 **Na handbook#16**: listener herstarten en één beurt van @odin in
      #general controleren. Eerder herstarten laat de hub fail-closed wegvallen
      (`odin.md` bestaat dan nog niet).
- [x] 1.9 `create-session-identity.py` zet nieuwe sessies in **#escalatie** in
      plaats van #general — anders krijgt een nieuwe sessie een lidmaatschap van
      precies het kanaal waar ze niet mag posten.
- [ ] 1.10 **Wacht op Mark** (classifier weigert de agent lidmaatschap te
      wijzigen): de bestaande sessies zijn nog geen lid van #escalatie. Voor
      odin-worker:
      `python3 ~/boomhuis/orchestrator/add-member.py --channel c1a0db51-3c96-46f9-9afa-1f03acfd87a3 --pubkey 3c9d7c6370738600512fb3be7bb2ed539dd7827a9bfc504d66c2bdb31bc18792 --role member`
- [ ] 1.8 **Besluit Mark**: `archivaris` had alleen #general — eigen kanaal of
      geen chat-facet meer?
