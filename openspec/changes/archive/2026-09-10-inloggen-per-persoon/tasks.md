# Tasks — inloggen-per-persoon

## 1. Opslag en credentials

- [x] 1.1 `chat/auth_store.py`: SQLite op 0600 in `/var/lib/boomhuis`
      (personen, sessies, uitnodigingen), met migratie bij eerste start.
- [x] 1.2 Wachtwoordhash met `hashlib.scrypt`; parameters bij de hash, zodat ze
      later omhoog kunnen zonder iedereen buiten te sluiten. N=2**14 en niet
      hoger: scrypt gebruikt 128*N*r bytes en OpenSSL weigert boven 32 MB met
      "memory limit exceeded" — 2**15 viel daar precies buiten. Gevonden door de
      unittest, niet door de eerste echte login.
- [x] 1.3 TOTP (RFC 6238, `hmac`) als optionele tweede factor per persoon,
      inclusief het intrekken ervan.

## 2. Sessies

- [x] 2.1 Aanmaken, verlengen, verlopen en intrekken; één sessie of allemaal.
- [x] 2.2 Cookie: HttpOnly, SameSite=Lax, Secure buiten localhost.
- [x] 2.3 Sessiegebonden CSRF-token voor elk statuswijzigend verzoek.

## 3. Toegang tot de API

- [x] 3.1 Elke `/api/`-route achter een sessie; zonder sessie 401, ook lezen.
- [x] 3.2 Rem op inlogpogingen per account én per bron, met oplopende wachttijd
      en hetzelfde antwoord voor onbekende gebruiker en fout wachtwoord.
- [x] 3.3 `BOOMHUIS_APP_TOKEN` verdwijnt als authenticatiemiddel.

## 4. Eerste start en uitnodigen

- [x] 4.1 Geen accounts → de server drukt een eenmalige setup-link af; wie die
      opent wordt eigenaar.
- [x] 4.2 Bestaat er al een `BOOMHUIS_APP_TOKEN` en nog geen account, dan mag
      dat token éénmalig de eigenaar aanmaken (migratiepad).
- [x] 4.3 Eenmalige, verlopende uitnodigingslinks; ingetrokken kunnen worden.

## 5. De app

- [x] 5.1 Inlogpagina (wachtwoord, en TOTP wanneer die aanstaat), in de shell
      van de service worker én in de statics-allowlist van `server.py`.
- [x] 5.2 `app-auth.js` herschreven: geen apparaat-token meer; 401 stuurt naar
      inloggen en komt daarna terug waar je was.
- [x] 5.3 Bij een 401 (niet: een netwerkfout) worden de lokale momentopnamen
      gewist — anders leest de volgende persoon op dat apparaat oude berichten.
- [x] 5.4 Uitloggen, en "overal uitloggen".

## 6. Nameten

- [x] 6.1 Unittests: 97 groen (was 66). Hash- en TOTP-verificatie inclusief
      hergebruik van een code, sessieverval en overal-uitloggen, alleen de hash
      in de database, CSRF-weigering, geen gebruikersopsomming, de rem. En
      `test_server.py` bewaakt nu de nieuwe invariant: niets open behalve de
      inlogroutes en de shell, en de gate komt vóór het valideren van parameters.
- [x] 6.2 e2e tegen de VM: `inloggen.js` 15/15 (setup, herladen blijft ingelogd,
      tweede setup geweigerd, POST zonder CSRF 403, uitloggen wist de
      momentopnamen én de sessie, opnieuw inloggen, fout wachtwoord blijft
      staan met een melding). `api.sh` 38/38 bewijst de andere kant: zonder
      sessie lekt er niets. De bestaande suites loggen nu in via een gedeelde
      `inlog.js` — ui.js 20/20, offline-boot.js 16/16, deeplink.js 5/5, xss.js
      groen.
- [x] 6.3 `docs/how-to/` bijwerken: eerste start, iemand uitnodigen, iemand
      verwijderen.

## 7. Bewust nog niet

- [ ] 7.1 **Wachtwoord wijzigen en wachtwoord vergeten.** Staat niet in de spec
      van deze change en is er dus ook niet. Voor een product is dat te weinig:
      het is het eerste dat de volgende change moet doen. De weg terug staat
      zolang in `docs/how-to/inloggen.md` (accounts wissen, opnieuw setup).
- [ ] 7.2 Iemand verwijderen die je hebt uitgenodigd — zelfde change.
