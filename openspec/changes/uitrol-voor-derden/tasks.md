# Tasks — uitrol-voor-derden

## 1. De chat als image

- [x] 1.1 `Dockerfile` voor de chat: python3-slim, alleen de app, non-root,
      healthcheck op `/api/status`.
- [x] 1.2 Build-workflow die per tag een image publiceert met een concrete
      versie — nooit `latest`, net als `BUZZ_IMAGE`.
- [x] 1.3 `adminctl.py` blijft bruikbaar: `docker compose exec chat python3
      adminctl.py eigenaar <naam>`.

## 2. De stack

- [x] 2.1 `deploy/docker-compose.yml`: relay, postgres, redis, seaweedfs én
      chat, met gepinde images.
- [x] 2.2 Alle gepubliceerde poorten krijgen een expliciet bind-adres;
      standaard `127.0.0.1`. Ook de relay-poort, die nu op `0.0.0.0` staat.
- [x] 2.3 `auth.db` en de push-registraties in een named volume.
- [x] 2.4 `deploy/.env.example` met elke instelling die een installatie nodig
      heeft, en niets geheims erin.

## 3. Blootstelling

- [x] 3.1 De drie vormen documenteren: reverse proxy met TLS, VPN/tailnet,
      bewust LAN — met wat je bij de derde opgeeft.
- [x] 3.2 De app achter een proxy: `X-Forwarded-For` gebruiken we al voor de
      rem; controleren dat cookies (`Secure`) kloppen achter TLS-terminatie.

## 4. Nameten op een schone machine

- [x] 4.1 Verse VM, alleen docker: compose-bestand + env erheen,
      `docker compose up -d`, eigenaar aanmaken, inloggen. Zonder enige stap
      die niet in een bestand staat.
- [x] 4.2 Vanaf een andere machine: loopback-standaard betekent dat er niets te
      bereiken is tot de beheerder kiest.
- [x] 4.3 De bestaande e2e-suites tegen die verse installatie. **Deels**:
      `api.sh` 38/38 groen, `inloggen.js` groen voor het installatie-deel. De
      browser-suites `ui.js`/`deeplink.js`/`offline-boot.js`/`xss.js` zijn
      geschreven tegen Marks eigen installatie (>5 kanalen, kanaal `bouw`,
      kanaal `general`, GitHub-inhoud) en vergen een gezaaide fixture — dat is
      eigen werk, niet deze change. Vastgelegd in `chat/e2e/README.md`.

## 5. Documentatie

- [x] 5.1 `docs/how-to/installeren.md`: van niets naar ingelogd.
- [x] 5.2 `docs/how-to/inloggen.md` verwijst naar het compose-pad voor
      `adminctl`.

## 6. Marks eigen installatie

- [x] 6.1 Migratiepad opschrijven (auth.db en push_subs.json van host naar
      volume, systemd-unit uit): `docs/how-to/migreren-naar-compose.md`.
      **Uitvoeren pas na zijn go** — deze change levert het pad, niet de
      verhuizing.

## 7. Onderweg gevonden (in deze change opgelost)

- [x] 7.1 `adminctl` strandde zonder terminal in een `EOFError`, precies bij
      `docker compose exec -T … eigenaar` — het moment waarop een verse
      installatie zijn eerste account krijgt. Leest nu het wachtwoord van stdin
      (één regel; een tweede regel telt nog steeds als bevestiging).
- [x] 7.2 `BUZZ_MEDIA_BASE_URL` moet op `/media` eindigen, anders weigert de
      relay te starten. Stond fout in het eerste `.env.example`; gevonden door
      het op een schone machine te draaien.
- [x] 7.3 `deploy/sleutelpaar.sh`: de buzz-CLI kan geen sleutelpaar maken, dus
      "genereer een keypair" was een stap die in geen enkel bestand stond.
- [x] 7.4 De e2e-scripts namen aan dat `BOOMHUIS_URL` op een slash eindigt
      (`…:8090login`). Genormaliseerd.
