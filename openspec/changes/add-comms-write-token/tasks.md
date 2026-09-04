## 1. Server

- [x] 1.1 `BOOMHUIS_APP_TOKEN` uit de omgeving; leeg = uit (gedrag ongewijzigd).
- [x] 1.2 Token-check vóór de drie schrijfpaden, `hmac.compare_digest`, 401 bij ontbrekend/fout token; leespaden ongemoeid.
- [x] 1.3 Token komt nooit in een log, foutmelding of response terug.

## 2. PWA

- [x] 2.1 `X-App-Token` meesturen op alle schrijf-fetches, uit `localStorage`.
- [x] 2.2 Bij 401: om het token vragen, opslaan, verzoek herhalen; bij nogmaals 401 een nette melding.
- [x] 2.3 Geen token in de geserveerde HTML/JS.

## 3. Gate

- [x] 3.1 Test: uit = schrijven werkt zonder header; aan = 401 zonder/fout token, 200 met; lezen in beide gevallen open.
- [x] 3.2 Smoke tegen een echt draaiende server (geen mock), beide standen: gate
      uit → GET 200 en POST /api/send 200 mét relay-aanroep; gate aan → lezen 200,
      alle vijf POST-routes 401 zonder/fout token en **nul** relay-aanroepen bij
      die weigeringen, met juist token weer 200; token komt niet in het antwoord.
- [x] 3.3 Docs: `chat/README.md` + `docs/how-to/pwa-installeren.md` — de "geen login"-belofte klopt niet meer.

## 4. Deploy

- [ ] 4.1 `BOOMHUIS_APP_TOKEN` in `chat.env` op de relay-VM (niet in git), service herstart.
- [ ] 4.2 Live bewijs: schrijven zonder token 401, met token 200; lezen blijft 200.
- [ ] 4.3 Token aan Mark geven; hij voert het één keer in per apparaat.
