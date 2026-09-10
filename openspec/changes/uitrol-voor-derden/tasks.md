# Tasks — uitrol-voor-derden

## 1. De chat als image

- [ ] 1.1 `Dockerfile` voor de chat: python3-slim, alleen de app, non-root,
      healthcheck op `/api/status`.
- [ ] 1.2 Build-workflow die per tag een image publiceert met een concrete
      versie — nooit `latest`, net als `BUZZ_IMAGE`.
- [ ] 1.3 `adminctl.py` blijft bruikbaar: `docker compose exec chat python3
      adminctl.py eigenaar <naam>`.

## 2. De stack

- [ ] 2.1 `deploy/docker-compose.yml`: relay, postgres, redis, seaweedfs én
      chat, met gepinde images.
- [ ] 2.2 Alle gepubliceerde poorten krijgen een expliciet bind-adres;
      standaard `127.0.0.1`. Ook de relay-poort, die nu op `0.0.0.0` staat.
- [ ] 2.3 `auth.db` en de push-registraties in een named volume.
- [ ] 2.4 `deploy/.env.example` met elke instelling die een installatie nodig
      heeft, en niets geheims erin.

## 3. Blootstelling

- [ ] 3.1 De drie vormen documenteren: reverse proxy met TLS, VPN/tailnet,
      bewust LAN — met wat je bij de derde opgeeft.
- [ ] 3.2 De app achter een proxy: `X-Forwarded-For` gebruiken we al voor de
      rem; controleren dat cookies (`Secure`) kloppen achter TLS-terminatie.

## 4. Nameten op een schone machine

- [ ] 4.1 Verse VM, alleen docker: compose-bestand + env erheen,
      `docker compose up -d`, eigenaar aanmaken, inloggen. Zonder enige stap
      die niet in een bestand staat.
- [ ] 4.2 Vanaf een andere machine: loopback-standaard betekent dat er niets te
      bereiken is tot de beheerder kiest.
- [ ] 4.3 De bestaande e2e-suites tegen die verse installatie.

## 5. Documentatie

- [ ] 5.1 `docs/how-to/installeren.md`: van niets naar ingelogd.
- [ ] 5.2 `docs/how-to/inloggen.md` verwijst naar het compose-pad voor
      `adminctl`.

## 6. Marks eigen installatie

- [ ] 6.1 Migratiepad opschrijven (auth.db en push_subs.json van host naar
      volume, systemd-unit uit). **Uitvoeren pas na zijn go** — deze change
      levert het pad, niet de verhuizing.
