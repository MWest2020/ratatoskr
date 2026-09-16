---
status: current
last_reviewed: 2026-09-11
---

# Ratatoskr installeren

Van een lege machine naar ingelogd. Je hebt nodig: een Linux-machine met docker
en docker compose, en tien minuten. Verder niets — geen checkout, geen buildstap,
geen contact met ons.

## 1. De bestanden

```bash
mkdir -p /opt/ratatoskr && cd /opt/ratatoskr
curl -fsSLO https://raw.githubusercontent.com/MWest2020/ratatoskr/main/deploy/docker-compose.yml
curl -fsSL  https://raw.githubusercontent.com/MWest2020/ratatoskr/main/deploy/.env.example -o .env
chmod 600 .env
```

## 2. Invullen

Open `.env`. Alles wat leeg is, moet je zetten; de rest heeft een werkbare
default. De secrets maak je zelf:

```bash
openssl rand -hex 32     # per secret één keer draaien
```

Drie dingen die je écht goed moet zetten:

- **`CHAT_IMAGE`** — een gepinde versie. Nooit `latest`: je wilt kunnen zeggen
  wélke Ratatoskr er draait.
- **`RELAY_OWNER_PUBKEY`** — de Nostr-pubkey (64 hex) van de eigenaar.
- **`RATATOSKR_URL`** — de URL waarop mensen de chat straks openen. Uitnodigings-
  en setup-links worden hiermee gebouwd; staat hier iets anders dan wat mensen
  in hun browser hebben, dan wijzen die links nergens heen.

## 3. Starten

```bash
docker compose up -d
docker compose ps          # alles 'healthy'? dan staat het
```

## 4. De eerste persoon

De installatie begint zonder gebruikers. De eigenaar maak je op de machine zelf,
want dat is het enige moment waarop er nog niemand is om het je te laten doen:

```bash
docker compose exec chat python3 adminctl.py owner <naam>
```

Dat vraagt tweemaal om een wachtwoord en zet de eigenaar in de database. Daarna
open je `RATATOSKR_URL`, log je in, en nodig je de rest uit vanuit de app
(kanalenlade → *Iemand uitnodigen*). Zie [inloggen.md](inloggen.md).

## Waar is dit bereikbaar?

Standaard: **alleen op de machine zelf** — `BIND_ADDR` voor de chat,
`RELAY_BIND_ADDR` voor de relay. Twee knoppen, want twee soorten publiek: mensen
komen bij de chat (via een proxy of tunnel), terwijl agents en andere machines
rechtstreeks met de relay praten. Draaien je agents op dezelfde machine, dan
blijven beide op `127.0.0.1`. Draaien ze elders, dan zet je alleen
`RELAY_BIND_ADDR` open — niet de chat.

Tot jij kiest, is er van buiten niets te bereiken. Drie manieren om te kiezen:

### Reverse proxy met TLS (het gewone geval)

Zet nginx/Caddy/Traefik ervoor die TLS termineert en doorstuurt naar
`127.0.0.1:8090`. Laat `BIND_ADDR` op `127.0.0.1` staan — de proxy zit op
dezelfde machine. Zorg dat de proxy `X-Forwarded-For` zet: de snelheidsrem in de
inlogroute gebruikt die om per bron te tellen, en zonder die header telt hij
alle verkeer als één bron.

`RATATOSKR_URL` is dan je `https://`-adres. De app zet zijn sessiecookie als
`Secure` zodra hij niet op localhost draait, dus **zonder TLS blijf je uitgelogd
in een lus** — dat is geen bug maar de bedoeling.

### VPN of tailnet

Zet de tunnel ervoor (bij ons: `tailscale serve`). De tunnel is dan je proxy en
`BIND_ADDR` blijft `127.0.0.1`. Voordeel: de netwerklaag is een control erbij, en
je hebt geen publiek certificaat nodig.

### Bewust op het LAN

`BIND_ADDR=0.0.0.0`. Mag, maar weet wat je opgeeft: de netwerklaag verdwijnt als
control en het inloggen is dan je enige. Alles wat er dan nog staat — scrypt,
optioneel TOTP, opaque sessies, een rem op raden — moet het alleen doen, en het
verkeer is plat HTTP tenzij je alsnog TLS ervoor zet. Doe dit op een thuisnet dat
je vertrouwt, niet op een kantoornet en zeker niet op een publiek IP.

## Wat waar blijft staan

De staat (`auth.db` met personen en sessies, de push-abonnees) staat in het named
volume `ratatoskr-chat-data`, niet in de map waar je dit bestand neerzette. Dus:

- `docker compose down` en weer `up` — alles is er nog, ook na een image-upgrade.
- `docker compose down -v` — **weg**, inclusief personen en wachtwoorden.

Upgraden is `CHAT_IMAGE` bijwerken en `docker compose up -d`. Gaat er iets mis,
zet de oude tag terug: de vorige image bestaat nog steeds, want hij was gepind.

## Als het niet werkt

- `docker compose ps` toont `unhealthy` bij **chat**: kijk met
  `docker compose logs chat`. Meestal een leeg `BUZZ_PRIVATE_KEY` of een relay
  die nog niet klaar is.
- Inloggen lukt niet en je ziet geen foutmelding: check `RATATOSKR_URL` en of je
  via `https` binnenkomt (zie de cookie-opmerking hierboven).
- De app laadt maar toont geen kanalen: de chat praat met de relay over het
  interne netwerk. `docker compose logs relay` — staat die `healthy`?

## Draaien de timers ook echt?

`bash verify.sh` vergelijkt de geïnstalleerde systemd-units met git
(`scripts/check_units.py`) én kijkt of ze bij hun laatste run geslaagd zijn
(`scripts/check_timers.py`).

Dat tweede is geen luxe. Een systemd-timer blijft `active (waiting)` en plant
netjes de volgende run, ongeacht hoe de vorige afliep — een dode taak ziet er van
buiten gezond uit. Op 2026-09-16 bleek `claude-secret-refresh.service` 82 keer
op rij te zijn omgevallen in veertien dagen, terwijl de timer al die tijd groen
oogde.

Een melding ziet er zo uit:

    — timers
      GEFAALD  claude-secret-refresh.service  (Result=exit-code, exit=255)

De reden staat altijd in het journaal, niet in de timer:

    journalctl --user -u <service> -n 30
