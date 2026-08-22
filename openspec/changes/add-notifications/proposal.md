## Why

De relay staat (fase 0), maar er stroomt nog niets doorheen. De grootste pijn
van vandaag is dat escalaties alleen bestaan als Mark aan tmux zit en dat
run-uitkomsten nergens landen buiten een branch. Fase 1 maakt van de relay een
levende feed: elke habitat-run post zijn start en verdict, elke escalatie
bereikt Mark op desktop én telefoon — zonder één byte wijziging aan de kooi.

## What Changes

- **Kanaaltopologie**: vaste kanalen per functie — `#runs` (machinale feed),
  `#escalatie` (alles wat een menselijk besluit vergt), `#bouw`, `#review`,
  `#architectuur`, `#marketing` — met threads per change/run. Geen kanaal per
  agent.
- **`notify/buzz-notify.sh`**: dun script rond `buzz-cli` (JSON in/uit) dat als
  orchestrator-identiteit post. Aangeroepen vanaf de orchestrator-host, ná
  `dispatch.sh`-uitkomsten; best-effort en nooit blokkerend voor een run.
- **Habitat-kant**: géén wijziging aan `cage/`, `worker/` of de
  CiliumNetworkPolicy. Alleen de orchestrator-werkwijze (buiten de kooi) krijgt
  er een stap bij; of dat via een wrapper of een mandaat-regel gaat is een
  apply-detail.

## Capabilities

### New Capabilities

- `channel-topology`: de vaste kanalen, hun functie en de thread-conventie.
- `run-notifications`: run-lifecycle en escalaties als berichten — post-only,
  buiten de kooi, zonder geheimen, en nooit een run blokkerend.

### Modified Capabilities

<!-- Geen in deze repo; habitats specs blijven onaangeroerd. -->

## Impact

- De tmux-escalatie blijft bestaan; buzz spiegelt hem. Pas als dit maanden
  betrouwbaar loopt is "buzz als primair escalatiekanaal" een eigen change.
- Mobiel bereik hangt af van de open beslissing intern/VPN vs publiek+TLS
  (project.md); een eventuele push-gateway is een aparte, latere change.
- Nieuw klein aanvalsoppervlak: de orchestrator-host houdt een Nostr-privésleutel
  (SOPS+age, zoals alle secrets).
