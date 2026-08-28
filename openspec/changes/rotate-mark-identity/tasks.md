# Tasks: rotate-mark-identity

- [x] 1. Nieuwe keypair genereren (buzz-admin generate-key); npub/nsec afgeleid + bech32-zelfcheck
- [x] 2. Nieuwe pubkey als relay-member toegevoegd
- [x] 3. SOPS secrets/identities.yaml: mark nsec+privkey_hex bijgewerkt (bytevergelijking groen)
- [x] 4. identities.yml: nieuwe pubkey/npub + geroteerd-datum
- [x] 5. Script rotate-mark.sh + nieuwe secret op vm 109 klaargezet (root, 0600/0700)
- [ ] 6. **Mark draait** `sudo /root/rotate-mark.sh` (kanaal-admins, owner-flip, chat-flip, verificatie, oude key eruit) — agent-permissielaag blokkeert membership-mutaties
- [ ] 7. Na groen: change archiveren + journal
