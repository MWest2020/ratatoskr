# Tasks: rotate-mark-identity

- [x] 1. Nieuwe keypair genereren (buzz-admin generate-key); npub/nsec afgeleid + bech32-zelfcheck
- [x] 2. Nieuwe pubkey als relay-member toegevoegd
- [x] 3. SOPS secrets/identities.yaml: mark nsec+privkey_hex bijgewerkt (bytevergelijking groen)
- [x] 4. identities.yml: nieuwe pubkey/npub + geroteerd-datum
- [x] 5. Script rotate-mark.sh + nieuwe secret op vm 109 klaargezet (root, 0600/0700)
- [x] 6. **Mark draaide** `sudo /root/rotate-mark.sh` (kanaal-admins, owner-flip, chat-flip, verificatie, oude key eruit) — agent-permissielaag blokkeert membership-mutaties
- [x] 7. Na groen: change archiveren + journal

Uitvoering 2026-08-28 door Mark: ROTATIE-KLAAR — 6/6 kanalen admin (accepted),
owner-flip + relay healthy, chat-API ok, media-get ok, oude key verwijderd en
geweigerd. Secret-bestand op de VM door het script gewist.
