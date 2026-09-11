# Change: uitrol-voor-derden

## Why

Tweede change richting het product (na `inloggen-per-persoon`). De installatie
moet los kunnen van Marks tailnet én van Marks handen. Vandaag kan geen van
beide, en dat zit in twee dingen die je pas ziet als je op de machine kijkt.

**De app wordt niet uitgerold, hij wordt gekopieerd.** De chat draait als
systemd-unit op `python3 /opt/buzz-build/chat/server.py`, uit een map die met
`scp` gevuld wordt en die verder een Rust-buildboom, een APK en cargo-caches
bevat. Er is geen image, geen versie, geen manier om te zeggen wélke boomhuis
er draait. Voor een derde is dat geen installatie maar een reconstructie.

**En de tailnet-eis klopt niet meer met wat er staat.** De spec zegt "geen
binding aan een publiek interface" en "van buiten het tailnet komt er geen
verbinding tot stand". Gemeten op de VM luistert de relay op `0.0.0.0:3000`
— elke machine op het LAN kan een TCP-verbinding opzetten. Die wordt daarna
op Nostr-niveau geweigerd omdat de relay closed is, dus het is geen open deur;
maar het is wél iets anders dan de spec belooft, en dat verschil moet weg
voordat iemand anders hierop bouwt.

Sinds `inloggen-per-persoon` is de netwerklaag ook niet meer de enige control:
elke aanroep hoort bij een persoon. Daarmee wordt "waar is dit bereikbaar" een
keuze van de beheerder in plaats van een invariant van het ontwerp.

## What changes

- **De chat wordt een image** dat uit deze repo gebouwd wordt, met een gepinde
  tag, en draait als service in dezelfde compose-stack als de relay. Geen
  `scp` meer, geen build-map als draaimap.
- **Staat gaat naar volumes**: `auth.db` en `push_subs.json` staan in een
  named volume in plaats van in `/var/lib/boomhuis` op de host, zodat een
  herinstallatie geen accounts kost.
- **Blootstelling wordt een expliciete keuze met een veilige standaard**:
  alles bindt op loopback tenzij de beheerder iets anders kiest. De gedocumenteerde
  opties zijn een reverse proxy met TLS, een VPN of tailnet, of bewust op het
  LAN. Ook de relay-poort krijgt een bind-adres in plaats van `0.0.0.0`.
- **Eén `.env.example` en één installatiepad** dat op een schone machine werkt:
  compose-bestand, env, `docker compose up -d`, en dan de eigenaar aanmaken.
- De tailnet-eis in de spec wordt een deployment-optie, met de eis dat de
  standaard níét publiek is.

## Wat hier NIET in zit

- **Marks eigen installatie migreren.** Dat is een aparte stap met zijn eigen
  risico (accounts en push-registraties verhuizen van host naar volume, de
  systemd-unit verdwijnt). Deze change levert het pad; wanneer zijn installatie
  eroverheen gaat is zijn keuze.
- **TLS zelf regelen.** De stack termineert geen TLS. Dat is werk voor de
  reverse proxy die de beheerder al heeft; wij documenteren wat we verwachten.
- Multi-tenancy, updates-over-de-lucht, of een installer met een schermpje.

## Impact

- Nieuw: `Dockerfile` voor de chat, `deploy/docker-compose.yml`,
  `deploy/.env.example`, een build-workflow die de image pint.
- `relay-deployment`: de tailnet-eis wordt een optie; er komt een eis bij over
  de standaard en over expliciete bind-adressen.
- `docs/how-to/`: installeren op een schone machine.
- Marks installatie blijft draaien zoals hij draait tot hij zelf migreert.
