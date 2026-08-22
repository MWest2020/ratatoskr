# Tasks: add-relay

- [ ] 1.1 Hostkeuze door Mark (VM/LXC, intern-of-publiek) — blokkerend, niet gokken
- [ ] 1.2 `deploy/`: upstream compose-bundle overnemen; `BUZZ_IMAGE` pinnen op een
      concrete SHA/semver; `.env.example` invullen zonder secrets
- [ ] 1.3 `secrets/`: age-key aanmaken/hergebruiken; relay-privésleutel,
      HMAC-secret en db/S3-credentials SOPS-versleuteld vastleggen
- [ ] 1.4 Relay starten in closed mode (`RELAY_OWNER_PUBKEY`), TLS conform de
      hostkeuze (Caddy of intern/VPN)
- [ ] 1.5 `identities.yml`: keypairs voor Mark (mens) en orchestrator (agent);
      npubs in de registry, privésleutels in `secrets/`
- [ ] 1.6 Clients aanmelden: desktop en mobiel voor Mark; `buzz-cli` werkend als
      orchestrator-identiteit vanaf de orchestrator-host
- [ ] 1.7 Live smoke vóór afronding: bericht Mark↔orchestrator in beide
      richtingen; vreemde pubkey aantoonbaar geweigerd; relay-herstart zonder
      identiteitsverlies
- [ ] 1.8 `docs/how-to/relay-herstel.md`: backup/restore beschreven en één keer
      echt geoefend
