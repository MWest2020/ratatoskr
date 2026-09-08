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
- [x] 1.7 Listener herstart na handbook#16; @odin antwoordt in #general en meldt
      in `#statistics` op het gedeclareerde model (`sonnet→claude-sonnet-5`).
      De herstart legde drie hardgecodeerde verwijzingen naar `coordinator` bloot
      (reader, hub-context, vlootlijst) — gefixt in #43, nu op rol.
- [x] 1.9 `create-session-identity.py` zet nieuwe sessies in **#escalatie** in
      plaats van #general — anders krijgt een nieuwe sessie een lidmaatschap van
      precies het kanaal waar ze niet mag posten.
- [x] 1.10 Lidmaatschappen gezet (Mark, 2026-09-07). Daarbij bleek het breder dan
      odin-worker: vijf van de acht agents zaten niet in #escalatie, dus de
      escalatieketen was in de praktijk dood. De listener meldt ontbrekende
      lidmaatschappen nu bij het opstarten (#44). Oorspronkelijke regel:
      `python3 ~/boomhuis/orchestrator/add-member.py --channel c1a0db51-3c96-46f9-9afa-1f03acfd87a3 --pubkey 3c9d7c6370738600512fb3be7bb2ed539dd7827a9bfc504d66c2bdb31bc18792 --role member`
- [x] 1.8 `archivaris` vervalt (besluit Mark): definitie verwijderd in
      handbook#15. Geen draaiende functionaliteit geraakt — hij had geen
      identiteit en stond niet in de run-lijst.
- [x] 1.11 **Losse bevinding, en mijn eerste diagnose was fout.** `_live.md`
      toonde archivaris als draaiende chat-agent en een allang gearchiveerde
      change als open. Ik noteerde "de liveness leest de handbook-registry" —
      onjuist: `live.py` leest `agents/agents.yml` en zijn eigen
      `openspec/changes`. De echte oorzaak was de **werkkopie**: `~/boomhuis`
      stond 52 commits achter met ongecommitte wijzigingen, en dáár stond
      archivaris nog in de run-lijst. Het gelijkzetten van die tree loste beide
      symptomen op.
      Zodat het niet stil terugkomt: `live.py` zet nu zijn herkomst onderaan
      (`branch@sha`) en zet een waarschuwing bovenaan als de checkout niet op
      main staat, achterloopt, of vuil is.
