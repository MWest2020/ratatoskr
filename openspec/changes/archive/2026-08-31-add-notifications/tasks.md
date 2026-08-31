# Tasks: add-notifications

- [x] 1.1 Kanalen aanmaken conform de topologie-spec; beschrijving per kanaal in
      het kanaal zelf
- [x] 1.2 `notify/buzz-notify.sh`: post run-start en run-einde (rol, change,
      repo, run-id, verdict, kosten, branch, link run-rapport) als thread in
      `#runs`; bare script, geen ceremonie
- [x] 1.3 Escalatiepad: elke escalatie uit de habitat-matrix ook naar
      `#escalatie`, met link naar het HTML-run-rapport
- [x] 1.4 Faalgedrag bewijzen: relay plat → dispatch en run verlopen normaal,
      gemiste notificatie zichtbaar in het lokale log
- [x] 1.5 Geheimen-check: berichten bevatten aantoonbaar geen PAT's, sleutels of
      privé-repo-inhoud (alleen metadata + links)
- [ ] 1.6 Live smoke vóór afronding: één echte habitat-run (wordsworth of
      testrepo) met start- en verdict-post in `#runs` en één geforceerde
      escalatie die Marks telefoon bereikt
- [ ] 1.7 Kooi-bewijs: `git diff` op habitats `cage/` en `worker/` is leeg
