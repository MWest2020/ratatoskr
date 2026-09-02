# Tasks: add-session-identities

- [x] 1.1 orchestrator/create-session-identity.py (keypair + SOPS-nsec + registry
      rol `sessie` + relay/#general-lid + profiel; geen handbook-def/run-lijst).
- [x] 1.2 ping.sh: IDENT-param (default bouwer) met rol-filter (alleen
      sessie/chat-agent; nooit de mens-identiteit).
- [x] 1.3 Identiteiten aangemaakt + getest (hubby postte onder eigen sleutel).
- [x] 1.4 Hardening (review): SOPS fail-closed (geen plaintext naar git bij een
      encrypt-fout); datum via date.today(); pad uit script-locatie; secret vóór
      registry; relay-add-member returncode gecheckt; SPDX-header; design.md +
      README bijgewerkt.
