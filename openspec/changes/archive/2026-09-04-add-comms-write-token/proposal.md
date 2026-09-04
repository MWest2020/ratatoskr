## Why

De security-pass van 2026-08-30 vond dat de chat-backend op `0.0.0.0` bond,
geen enkele authenticatie had en élk bericht als **`mark`** ondertekende. Dat is
gedicht op de netwerklaag: de backend luistert nu op loopback en gaat er via
`tailscale serve` met HTTPS uit. Vanaf het LAN is er niets meer te bereiken.

Wat daarmee **niet** is opgelost: iedereen die het tailnet al binnen is, kan nog
steeds `POST /api/send` doen en post dan als Mark. Vandaag is dat theoretisch —
elke tailnet-node is Marks eigen hardware. Het wordt echt zodra dat niet meer
geldt: een apparaat van iemand anders toelaten, een uitgelekte ephemeral
auth-key, een node die code draait die Mark niet schreef, een gedeelde node via
Tailscale-sharing, of een gestolen telefoon die nog geautoriseerd is.

De baton hield dit bewust open als "optioneel, defence-in-depth, Marks keuze".
Dit is die keuze.

## What Changes

- **`BOOMHUIS_APP_TOKEN`** (uit `chat.env` op de relay-VM, nooit in git). Staat
  hij leeg → gedrag ongewijzigd, de netwerklaag blijft de enige control. Staat
  hij gezet → de **schrijf**-endpoints (`/api/send`,
  `/api/channels/create`, `/api/channels/delete`) eisen een `X-App-Token` die
  constant-time gelijk is; ontbreekt of klopt niet → **401**.
- **Lezen blijft open.** De PWA moet kunnen renderen vóór je iets kunt typen, en
  het tailnet gatet de leeskant al. Alleen schrijven — het gedrag dat zich als
  Mark voordoet — komt achter het token.
- **De PWA vraagt het token één keer per apparaat** en bewaart het in
  `localStorage`. Bij een 401 vraagt hij opnieuw en herhaalt het verzoek. Het
  token wordt **nooit** door de server in de pagina gezet (zie design.md).
- **Agents raken dit niet.** `ping.sh` en de chat-native agents tekenen zelf met
  hun eigen nsec tegen de relay; ze gebruiken deze HTTP-API niet. Geverifieerd:
  de enige aanroepers van de schrijf-endpoints zijn `chat/app.js` en
  `chat/app-ui.js`.

## Capabilities

### Modified Capabilities
- `webchat-pwa`: schrijven vereist een apparaat-token wanneer de deployment er
  een zet; de how-to beschrijft dat eerlijk (het was "geen login en geen sleutel
  in de browser" — dat klopt niet meer zodra het token aanstaat).

## Impact

- Code: `chat/server.py` (token-check vóór de drie schrijfpaden),
  `chat/app.js` + `chat/app-ui.js` (token meesturen, 401 → prompt → opnieuw),
  `chat/README.md` + `docs/how-to/pwa-installeren.md`.
- Deployment: `BOOMHUIS_APP_TOKEN` in `chat.env` op de relay-VM + herstart.
  Mark voert het token één keer in per apparaat (telefoon, desktop).
- Niet-breekend zolang de env-var leeg blijft; zodra hij gezet is, is een
  apparaat zonder token read-only tot het token is ingevoerd.
- Bestandsgrenzen: `server.py` blijft onder de 200 regels.
