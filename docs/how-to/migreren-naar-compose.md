---
status: current
last_reviewed: 2026-09-11
---

# Marks eigen installatie naar compose

De relay draait al in compose (`/opt/buzz-relay`, project `buzz-prod`). De chat
niet: die draait als systemd-unit op `/usr/bin/python3
/opt/buzz-build/chat/server.py`, uit een map die met `scp` gevuld is. Dit is het
pad naar dezelfde uitrol als een derde krijgt.

**Dit document is het pad, niet de verhuizing.** Uitvoeren pas na Marks go — het
zet zijn chat een paar minuten stil en verplaatst zijn accountdatabase.

## Wat er verhuist

| nu | straks |
|---|---|
| `/opt/buzz-build/chat/` (scp-kopie) | image `CHAT_IMAGE`, gepinde tag |
| `boomhuis-chat.service` (systemd) | service `chat` in de compose-stack |
| `/opt/buzz-build/chat/chat.env` (root:600) | `.env` naast het compose-bestand |
| `/var/lib/boomhuis/auth.db` (+ `-wal`, `-shm`) | volume `ratatoskr-chat-data` |
| `/var/lib/boomhuis/push_subs.json` | hetzelfde volume |

De relay, postgres, redis en seaweedfs blijven staan waar ze staan, met hun
volumes. `tailscale serve` blijft naar `127.0.0.1:8090` wijzen — de chat
publiceert straks op dezelfde poort, alleen uit een container.

## Stappen

1. **Image publiceren** en de tag noteren (workflow `chat-image`, tag
   `chat-v<versie>`). Zonder gepubliceerd image kan de stack niet starten.

2. **Compose samenvoegen.** `deploy/docker-compose.yml` uit deze repo is de
   vendored versie van wat er op de VM staat, plus de `chat`-service. Neem hem
   over als `/opt/buzz-relay/docker-compose.yml` en vergelijk eerst:

       diff /opt/buzz-relay/docker-compose.yml deploy/docker-compose.yml

   Let op `COMPOSE_PROJECT`: het project heet daar `buzz-prod`. Zet dat in
   `.env`, anders maakt compose een tweede set volumes aan onder de naam
   `boomhuis` en staat de relay ineens leeg.

3. **`.env` aanvullen** met de chat-regels uit `chat.env` (`BUZZ_PRIVATE_KEY`,
   `BUZZ_ORCHESTRATOR_KEY`, `VAPID_PUBLIC`, `GITHUB_TOKEN`, `RATATOSKR_URL`) en
   `CHAT_IMAGE`. Het oude `APP_TOKEN` gaat **niet** mee: dat is dood sinds
   `inloggen-per-persoon`.

   Let op de twee bind-knoppen, want ze staan hier niet gelijk:

       BIND_ADDR=127.0.0.1        # chat — tailscale serve zit ervoor
       RELAY_BIND_ADDR=0.0.0.0    # relay — agent-lxc praat er over het LAN mee

   Zet je de relay óók op loopback, dan verliezen de listener, de jobs en
   `ping.sh` op agent-lxc hun verbinding. Dit is precies zoals het vandaag al
   staat (`ss -ltnp`: chat op 127.0.0.1:8090, relay op 0.0.0.0:3000) — de
   migratie verandert de blootstelling niet.

4. **Chat stilzetten** (nu pas, zodat de database niet meer beweegt):

       sudo systemctl stop boomhuis-chat && sudo systemctl disable boomhuis-chat

5. **Staat in het volume zetten.** Het volume bestaat nog niet, dus laat compose
   het maken en kopieer erin:

       docker compose create chat

   **Let op:** `create` raakt niet alleen de chat. Elke service waarvan de config
   veranderde wordt óók opnieuw aangemaakt — en blijft dan in `Created` staan,
   dus gestopt. De relay valt daaronder (zijn `ports` kreeg een expliciet
   bind-adres). Gemeten 2026-09-11: de relay lag daardoor ruim een minuut plat en
   alle agents waren los. Controleer direct na deze stap:

       docker compose ps -a        # staat er iets op 'Created'?
       docker compose up -d        # zet alles weer aan
       vol=$(docker volume inspect -f '{{.Mountpoint}}' buzz-prod_ratatoskr-chat-data)
       sudo cp -a /var/lib/boomhuis/auth.db* /var/lib/boomhuis/push_subs.json "$vol"/
       sudo chown -R 10001:10001 "$vol"

   De `-wal` en `-shm` horen erbij: SQLite in WAL-modus zet recente schrijfacties
   daarin. Alleen `auth.db` kopiëren kan een sessie of een wachtwoordwijziging
   kosten. Uid 10001 is de `boomhuis`-gebruiker in het image.

6. **Starten en kijken:**

       docker compose up -d          # niet alleen `up -d chat`, zie stap 5
       docker compose logs -f chat

   Verwacht `[chat] luistert op 0.0.0.0:8090` en géén setup-link — die verschijnt
   alleen als er nog geen account is, dus als je hem ziet, is stap 5 misgegaan.

7. **Nameten.** Inloggen in de PWA, een kanaal openen, een bericht sturen. En:

       RATATOSKR_URL=https://boomhuis-relay.tail8f7877.ts.net bash chat/e2e/api.sh

## Terug als het misgaat

De oude weg staat er nog:

    docker compose stop chat
    sudo systemctl enable --now boomhuis-chat

De systemd-unit leest nog steeds `/var/lib/boomhuis/auth.db` — dat bestand is
gekopieerd, niet verplaatst. Ruim het pas op als de compose-kant een paar dagen
staat.


## Kwam je van een installatie die al in compose draaide?

Dan heet het volume nog `…_boomhuis-chat-data` en het pad in de container nog
`/var/lib/boomhuis`. Kopiëren, niet verplaatsen — het oude volume is je weg terug:

    docker compose create chat        # maakt het nieuwe volume
    oud=$(docker volume inspect -f '{{.Mountpoint}}' <project>_boomhuis-chat-data)
    nieuw=$(docker volume inspect -f '{{.Mountpoint}}' <project>_ratatoskr-chat-data)
    sudo cp -a "$oud"/. "$nieuw"/
    sudo chown -R 10001:10001 "$nieuw"
    docker compose up -d              # niet alleen `up -d chat`, zie stap 5

Je `.env` mag de oude `BOOMHUIS_*`-namen houden: de app leest eerst
`RATATOSKR_*` en valt daarop terug. Hernoemen mag, hoeft niet, en kan later.
