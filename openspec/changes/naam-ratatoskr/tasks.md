# Taken

## 1. Code
- [x] 1.1 `chat/instellingen.py`: `lees(naam, default)` met terugval + tests
- [x] 1.2 Alle leesplekken in `chat/` door die functie
- [x] 1.3 `agents/`, `jobs/`, `orchestrator/`, e2e: idem waar van toepassing

## 2. Uitrol
- [x] 2.1 Image `ratatoskr-chat` in de workflow; oud pakket blijft staan
- [x] 2.2 `deploy/`: volume `ratatoskr-chat-data`, pad `/var/lib/ratatoskr`
- [x] 2.3 `.env.example` en de how-to's op de nieuwe namen

## 3. De draaiende installatie
- [ ] 3.1 Kopieerpad voor het volume in `migreren-naar-compose.md`
- [ ] 3.2 Uitvoeren: nieuw image, volume gekopieerd, inloggen werkt nog
- [ ] 3.3 systemd-units en checkout-map op agent-lxc

## 4. Repo
- [ ] 4.1 GitHub-repo hernoemen; remotes bijwerken
- [x] 4.2 README, `CLAUDE.md`, `openspec/project.md`
- [ ] 4.3 Change archiveren
