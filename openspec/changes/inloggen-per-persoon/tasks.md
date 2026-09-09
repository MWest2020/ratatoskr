# Tasks — inloggen-per-persoon

## 1. Opslag en credentials

- [ ] 1.1 `chat/auth_store.py`: SQLite op 0600 in `/var/lib/boomhuis`
      (personen, sessies, uitnodigingen), met migratie bij eerste start.
- [ ] 1.2 Wachtwoordhash met `hashlib.scrypt`; parameters bij de hash, zodat ze
      later omhoog kunnen zonder iedereen buiten te sluiten.
- [ ] 1.3 TOTP (RFC 6238, `hmac`) als optionele tweede factor per persoon,
      inclusief het intrekken ervan.

## 2. Sessies

- [ ] 2.1 Aanmaken, verlengen, verlopen en intrekken; één sessie of allemaal.
- [ ] 2.2 Cookie: HttpOnly, SameSite=Lax, Secure buiten localhost.
- [ ] 2.3 Sessiegebonden CSRF-token voor elk statuswijzigend verzoek.

## 3. Toegang tot de API

- [ ] 3.1 Elke `/api/`-route achter een sessie; zonder sessie 401, ook lezen.
- [ ] 3.2 Rem op inlogpogingen per account én per bron, met oplopende wachttijd
      en hetzelfde antwoord voor onbekende gebruiker en fout wachtwoord.
- [ ] 3.3 `BOOMHUIS_APP_TOKEN` verdwijnt als authenticatiemiddel.

## 4. Eerste start en uitnodigen

- [ ] 4.1 Geen accounts → de server drukt een eenmalige setup-link af; wie die
      opent wordt eigenaar.
- [ ] 4.2 Bestaat er al een `BOOMHUIS_APP_TOKEN` en nog geen account, dan mag
      dat token éénmalig de eigenaar aanmaken (migratiepad).
- [ ] 4.3 Eenmalige, verlopende uitnodigingslinks; ingetrokken kunnen worden.

## 5. De app

- [ ] 5.1 Inlogpagina (wachtwoord, en TOTP wanneer die aanstaat), in de shell
      van de service worker én in de statics-allowlist van `server.py`.
- [ ] 5.2 `app-auth.js` herschreven: geen apparaat-token meer; 401 stuurt naar
      inloggen en komt daarna terug waar je was.
- [ ] 5.3 Bij een 401 (niet: een netwerkfout) worden de lokale momentopnamen
      gewist — anders leest de volgende persoon op dat apparaat oude berichten.
- [ ] 5.4 Uitloggen, en "overal uitloggen".

## 6. Nameten

- [ ] 6.1 Unittests: hash- en TOTP-verificatie, sessieverval en intrekken,
      CSRF-weigering, geen gebruikersopsomming, de rem.
- [ ] 6.2 e2e: inloggen, herladen blijft ingelogd, uitloggen, 401 wist de
      momentopnamen, uitnodiging werkt één keer.
- [ ] 6.3 `docs/how-to/` bijwerken: eerste start, iemand uitnodigen, iemand
      verwijderen.
