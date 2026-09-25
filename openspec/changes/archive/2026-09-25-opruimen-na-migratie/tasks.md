# Taken

**Niet eerder dan 2026-09-18** (een week na de migratie), en alleen als de
compose-kant sindsdien niet is teruggedraaid.

- [x] 1.1 `after-deploy.sh` groen op de dag zelf — de drie lagen, niet één
      (2026-09-24: 39/0, 7/0, 12/0 — nadat de poort zelf weer kon falen, 963eee5)
- [x] 1.2 Homelab-PR: unit weg, `docker/buzz-relay/` verwijst naar `deploy/`
      (homelab f7ed2e4, direct op main; het playbook richt alleen nog de host in)
- [x] 1.3 `/opt/buzz-build/chat` opruimen op de VM (2026-09-25; op Marks
      verzoek heel `/opt/buzz-build`, ook de Android-bouwresten, en de oude
      unit in /etc/systemd/system — 11 GB vrij)
- [x] 1.4 Het oude volume `buzz-prod_boomhuis-chat-data` verwijderen — als
      laatste, en pas als 1.1 t/m 1.3 af zijn
      (2026-09-25; eerst als `/opt/buzz-relay/boomhuis-chat-data-final-2026-09-24.tgz`
      bewaard, 0600; daarna `after-deploy.sh` opnieuw groen: 39/0, 7/0, 12/0)
- [x] 1.5 `chat/README.md` en `docs/how-to/inloggen.md` bijwerken
- [x] 1.6 Change archiveren
