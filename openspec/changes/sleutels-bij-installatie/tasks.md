# Taken

- [x] 1.1 `agents/keystore.py`: backends `sops` en `bestand`, met fail-closed
      gedrag en een expliciete reden bij een ontbrekende sleutel
- [x] 1.2 Tests: beide backends, ontbrekende sleutel, te ruime rechten (0644 is
      geen sleutelopslag), en een nsec die geen nsec is — 12 tests
- [x] 1.3 Sleutelparen genereren in Python (dezelfde secp256k1+bech32 als
      `deploy/sleutelpaar.sh`), zonder docker
- [x] 1.4 `scripts/init_identities.py`: vult ontbrekende identiteiten aan,
      idempotent (O_EXCL: een bestaande sleutel wordt NOOIT overschreven),
      schrijft de publieke helft in de lokale `identities.yml`
- [x] 1.5 `agents/run.sh` kiest de backend via `RATATOSKR_KEYSTORE`; default
      blijft `sops`, dus Marks installatie verandert niet
- [x] 1.6 Spec `identity-registry` bijgewerkt
- [x] 1.7 Nagemeten op een verse map: twee identiteiten gegenereerd, rechten
      0700/0600, tweede run raakt niets aan, keystore leest ze terug
- [ ] 1.8 Nameten op Marks eigen installatie: listener herstarten op de
      `sops`-backend en zien dat alle acht agents nog starten
- [ ] 1.9 Change archiveren
