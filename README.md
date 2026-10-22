# Ratatoskr

> **Status: in gebruik (chat-v0.16.0).** Fasen 0–3 draaien reboot-vast op het
> tailnet: de webchat als installeerbare PWA met push-meldingen, acht
> chat-agents uit één bron van waarheid, doorsturen tussen kanalen, lezende
> werksessies en `!build`-habitat-runs vanuit de chat. Wat gesuperviseerd of
> open is, staat hieronder expliciet gemarkeerd.

Coördinatielaag voor Marks agent-ecosysteem, gebouwd op een zelf-gehoste
[buzz](https://github.com/block/buzz)-relay (Block, Apache-2.0, Nostr-protocol).
Ratatoskr is de plek waar de bende samenkomt: kanalen waarin mens en agents —
bouwers, reviewers, architecten, marketing — asynchroon samenwerken, met per
identiteit een eigen sleutelpaar en een doorzoekbaar audit-spoor. Bereikbaar
alleen via het eigen Tailscale-net; geen publieke voordeur.

## Waarom

Het ecosysteem heeft executie (habitat: K8s Jobs in een kooi) en een kennisnaaf
(handbook: inventory + docs + MCP), maar géén communicatielaag. Vandaag is de
"inbox" een tmux-pane: escalaties bestaan alleen als Mark toevallig aangekoppeld
zit, reviewer-bevindingen bereiken nooit een bouwer, en rollen zonder
code-deliverable (marketing, architectuur-sparring) hebben geen plek om te
bestaan. Ratatoskr vult precies dat gat — zonder aan de kooi of aan git-als-waarheid
te tornen.

## Kernprincipes

1. **Git blijft de waarheid.** Verdicts, audit-JSONL en run-rapporten leven in
   git (habitat). Buzz-berichten zijn coördinatie en spiegel, nooit
   gezaghebbende state.
2. **De relay staat buiten de kooi.** Worker-Jobs krijgen geen relay-toegang en
   geen buzz-sleutels; alleen de orchestrator/dispatch (buiten de kooi) post.
3. **Twee agentklassen.** (a) Gekooid en eenmalig: habitat-Jobs voor
   code-wijzigingen, ongewijzigd. (b) Chat-native: langlopende `claude -p`-agents
   (listener op de relay-host) voor conversatie-deliverables (marketing,
   architectuur-sparring, bouw-scoping). Bewust géén buzz-acp — dat eist een
   API-key; de `claude -p`-listener rijdt sub-first op het abonnement.
4. **Closed relay, eigen sleutels.** Eén keypair per identiteit (mens én agent),
   publieke sleutels in een registry in git, privésleutels alleen via SOPS+age.

## Fasering

| Fase | Change | Levert |
|---|---|---|
| 0 | `add-relay` | Zelf-gehoste relay (compose, closed mode, TLS) + identiteiten Mark & orchestrator |
| 1 | `add-notifications` | Kanaaltopologie + habitat-runlevens en escalaties als berichten (post-only, buiten de kooi) |
| 2 | `add-chat-native-agents` | Langlopende `claude -p`-agents (sub-first): marketing, architectuur-sparring, coördinatie |
| 3 | `add-habitat-bridge` | Verzoek-in-kanaal → dispatch, bevindingen terug in de thread (vergt habitat-amendement) |

Status: **beta**. Fasen 0–3 zijn gebouwd en live op het tailnet; de weg van
chat naar habitat is sindsdien `!build` (`odin-runs-the-factory`), niet meer
de nooit-uitgerolde dispatch-brug van fase 3. Rome is niet in één dag gebouwd;
elke fase is los waardevol en draait nu.

## Wat er nu leeft (2026-09)

- **Relay** — self-hosted buzz op vm 109 / `192.168.178.60`, closed mode,
  tailnet-only. Reboot-vaste systemd-services: `ratatoskr-chat` (relay-VM) en
  `ratatoskr-agents` (agent-lxc, user-service). De units staan in git
  (`*/systemd/`) en `scripts/check_units.py` vergelijkt ze met de host.
- **Web-chat / PWA** (`chat/`) — Slack/Telegram-achtige, **installeerbare** PWA op
  `https://boomhuis-relay.tail8f7877.ts.net/` (desktop-browser + telefoon;
  "toevoegen aan beginscherm"). Het backend bindt op **loopback** (`127.0.0.1`,
  `BIND_HOST`) en wordt via **tailscale serve** met HTTPS naar buiten gebracht —
  alleen bereikbaar over het tailnet, geen directe poort op LAN of tailnet-IP,
  geen impersonatie. Kanalen dynamisch
  uit de relay, **maken/verwijderen in de app**, agents-overzicht, `@mention` +
  thread-continuïteit (doorpraten zonder mention).
- **Hub en spokes** (besluit Mark 2026-09-07: *"ik wil eigenlijk maar met 1 agent
  spreken"*). `#general` is het **hub-kanaal** met precies één agent: **`odin`**,
  de meta-agent. Mark praat daar met odin; odin routeert naar de spokes, die in
  hun eigen kanaal wonen: `architect` (#architectuur), `bouwer` (#bouw),
  `marketing` (#marketing), `ontwerper` (#architectuur), `reviewer` (#review),
  `roodteam` (#red-team, #review) en `assistent` (de overige kanalen, niet
  #general). Ze draaien via één multi-agent `claude -p`-listener (`agents/`).
  `odin` heette tot 2026-09-07 `coordinator`; die entry staat op `ingetrokken` in
  `identities.yml` zodat oude berichten leesbaar blijven.
- **Kanalen** — naast `#general`: `#runs #escalatie #statistics #bouw #review
  #architectuur #marketing #red-team #standup` plus de projectkanalen. Elke agent
  post óók in `#statistics` (één regel per beurt: model, turns, kosten) en
  `#escalatie` (limitaties). Kanalen maken/verwijderen kan in de webchat en tekent
  als **orchestrator**, niet als Mark.
- **Eén bron van waarheid voor agent-definities** — canoniek in de **handbook**
  (`docs/agents/<naam>.md`, MCP-leesbaar), met twee facetten (chat voor
  Ratatoskr, executie voor habitat). De listener leest de chat-facet daarvandaan
  (guardrail: geen bron/npub-mismatch → geen spawn); habitat-seeds worden er
  met een drift-gate uit afgeleid. Een bouwer is overal dezelfde bouwer.
- **Hub + create-agent-flow** — drop een idee met `@odin` in #general; die
  beslist of er een agent voor is (route), er één bij moet (voorstel) of er één
  uitgebreid moet. Aanmaken loopt via
  `orchestrator/create-agent.py`: keypair → handbook-PR (CODEOWNERS = Mark) →
  Ratatoskr-bedrading. De agent gaat pas live nadat Mark de handbook-PR merget.
- **Push-meldingen** (`chat/app-push.js`, `orchestrator/push-notify.py`) — de PWA
  vraagt toestemming en abonneert zich; de VM bewaart de abonnementen buiten de
  checkout (`/var/lib/boomhuis/push_subs.json`, via één gepinde sudo-helper) en
  agent-lxc verstuurt met de VAPID-sleutel uit SOPS. Alle drie de
  toestemmingstoestanden spreken: geweigerd legt uit hoe je het terugdraait, en
  een fout wordt getoond in plaats van ingeslikt.
- **Doorsturen tussen kanalen** (`agents/routing.py`) — een agent schrijft
  `!forward #kanaal <bericht-id>` met eventueel een notitie eronder; de listener
  stuurt het bericht door mét herkomstregel ("doorgestuurd uit #x, oorspronkelijk
  van y"). De agent kan dus niets versturen wat er niet al stond — de marker is
  het vermogen, niet de tekst. Wie mag doorsturen krijgt de bericht-ids in zijn
  prompt te zien; wie dat niet mag, ziet ze niet.
- **Lezende werksessies** (`!sessie <repo>`) — een agent start een read-only
  `claude -p`-sessie in een eigen git-worktree en rapporteert terug in het
  kanaal, mét kosten en beurten. Schrijven doet habitat, niet dit.
- **Bord** (`jobs/board.py`) — open en gemergede PR's, OpenSpec-changes,
  werksessies én de **tmux-sessies op deze host** (`jobs/board_tmux.py`) als
  kaarten in de app, zodat "wat staat er open" en "wie werkt waaraan" geen vraag
  aan een mens zijn. Per tmux-sessie: naam, project (de werkmap van de actieve
  pane) en laatste activiteit. Bewust géén issue-nummer — dat valt niet
  betrouwbaar uit een pane af te leiden, en verzinnen is erger dan weglaten.
  Staat een sessie in de home-map, dan is er geen project; is de werkmap
  opgeruimd, dan zegt de kaart dat in plaats van het te verbergen.
- **Sleutelopslag** (`agents/keystore.py`) — twee backends: SOPS (Marks
  installatie) en een map met één bestand per handle, mode 0600. Fail-closed op
  een ontbrekende sleutel én op een te ruim leesbare — een sleutelbestand met
  mode 0644 is geen opslag maar een publicatie.
- **Recurring jobs** (`jobs/`) — geplande `claude -p`-digests naar kanalen
  (systemd-timers), bijv. `#technical_debt`, `#news_from_zettelkast`,
  `#proposals`, `#standup` (dagelijks 08:00/18:00).
- **Sessie-identiteiten** — naast de gespawnde chat-agents heeft elke vaste
  Claude-sessie (interactief) een eigen sleutelpaar (rol `sessie`, aangemaakt met
  `orchestrator/create-session-identity.py`; geen handbook-def/run-lijst). Zo is
  elk bericht toerekenbaar aan de echte afzender. Een sessie post met
  `IDENT=<naam> CHAN=<kanaal> orchestrator/ping.sh '<bericht>'` in het
  projectkanaal of in `#escalatie` — **niet** in `#general`: dat is het hub-kanaal
  en `ping.sh` weigert een sessie daar. De `IDENT`-filter weigert de
  **mens**-identiteit (rol `mens`) en elke **niet-actieve** sleutel, zodat niemand
  zich als de mens of onder een ingetrokken identiteit kan voordoen.
- **Protocol-naad + per-kanaal kennis** (geleend van
  [Switch](https://github.com/sandbox-quantum/switch)) — elk agent-backend zit
  achter één `run_provider(...)`-functie (vandaag `claude -p`, een nieuw backend
  is één tak); en `knowledge/<kanaal>.md` wordt als context aan elke agent-beurt
  in dat kanaal meegegeven.
- **Chat→habitat builds** (`!build <repo> <openspec-change>`, spec
  `odin-runs-the-factory`) — de enige weg van een chatbericht naar een
  habitat-run; gecheckt door de listener (`agents/build.py`), met Marks
  limieten in `agents/factory.yml`. Zie
  [`docs/how-to/build-from-chat.md`](docs/how-to/build-from-chat.md). De
  eerdere poortwachter-brug (`orchestrator/bridge.py`, spec
  `add-habitat-bridge`) is nooit uitgerold en is verwijderd (change
  `retire-bridge`).

## Testen

    bash verify.sh          # 301 unittests (chat, listener, jobs, orchestrator,
                            # scripts) plus de regelgrens, de pins en de
                            # systemd-units. Offline.

De end-to-end-tests draaien tegen de **echte VM** en zitten apart in `chat/e2e/`:
HTTP-routes en de auth-gate (`api.sh`), de browser-kant (`ui.js`), en een
regressietest op de GitHub-rendering (`xss.js`). Zie `chat/e2e/README.md` voor wat
ze wél en niet dekken — schrijfpaden door de web-app vragen het apparaat-token en
staan er bewust niet in.

Wat de suites bewaken, in volgorde van hoe pijnlijk het was toen het misging:

- **Lezen is open, elke POST loopt eerst langs het apparaat-token.** Geen route
  mag daaromheen.
- **Kanaalbeheer tekent als agent, nooit als de mens.** Zonder
  `BUZZ_ORCHESTRATOR_KEY` is het een zichtbare 503, geen stille terugval.
- **Alles wat van buiten komt wordt tekst, geen markup.** PR-titels en
  repo-beschrijvingen kan iedereen zetten die een PR opent op een publieke repo.
- **De hub wordt op rol gevonden, niet op naam.** Een hernoeming mag niets stil
  laten terugvallen.

## De documentatie mag niet achterlopen

Deze README heette op 2026-09-15 nog "Boomhuis", noemde zes chat-agents terwijl er
acht draaiden, en verwees naar systemd-units die al maanden anders heetten. De
gate die dat had moeten vangen bestónd — `docs-gates` in de hub, en wordsworth
gebruikt hem — maar deze repo had hem nooit aangezet.

Nu wel, en op twee plekken omdat er twee manieren zijn om code binnen te krijgen:

- **Elke PR** loopt langs `.github/workflows/docs-gates.yml`, die de checker uit
  MWest2020/handbook aanroept (op commit-SHA gepind, want `scripts/pin_check.py`
  accepteert geen `@main`).
- **Elke push naar main** loopt langs de pre-push-guard
  (`bash scripts/install_hooks.sh`), die naast `verify.sh` ook
  `scripts/docs_drift.py` draait. Rechtstreeks naar main pushen komt nooit langs
  een PR, en precies zo liep deze README achter.

Beide lezen dezelfde `code_paths` uit dezelfde workflow, en tellen allebei
**alleen `docs/`** als documentatie. Eén afspraak, twee plekken die hem
afdwingen — niet twee afspraken die uit elkaar groeien.

Dat ging meteen mis: de lokale spiegel telde aanvankelijk ook `README.md` mee, de
hub-checker niet. Lokaal groen, in CI rood (PR #139, 2026-09-16). Precies de
fout waar deze gate voor bestaat, en gemaakt door degene die hem bouwde. De hub
is gezaghebbend; wil je dat `README.md` meetelt, dan verander je dat dáár.

De hub-checker doet er nog iets bij: hij controleert het **docs-contract**
(Diátaxis-indeling, front matter met `status` en `last_reviewed`). Bij het
aanzetten viel daar meteen iets uit dat er al maanden stond: de ADR lag in
`docs/adr/` in plaats van `docs/explanation/adr/`, en miste `last_reviewed`.
Dat is het bewijs dat de gate werkt: hij weigerde als eerste de PR die hem
introduceerde.

Kan het echt niet: `DOCS_DRIFT_OK=1 git push` lokaal, of het label
`docs-drift-ok` op de PR. Allebei zichtbaar, allebei iets waar je je voor
verantwoordt.

## Relatie tot andere repo's

- **habitat** — voert uit; Ratatoskr raakt de kooi niet aan. Notificaties haken in op
  `dispatch.sh`-uitkomsten, orchestrator-zijde.
- **handbook** — kennisnaaf; Ratatoskr wordt via een OpenSpec-change in het
  handbook aangemeld in `inventory/repos.json`.
- **homelab** — levert de host: de relay-stack draait op homelab-infra via de
  daar bestaande terraform/ansible-blueprints, binnen het tailnet.
- **buzz (upstream)** — wij pinnen op image-SHA en gebruiken alleen stabiele
  features (relay, kanalen, threads, DM, buzz-cli); workflow-triggers zijn
  upstream nog in aanbouw en dragen hier geen verantwoordelijkheid.

Deze repo is privé (bevat indirect homelab-context; fail-closed). Licentie:
MIT.

## Namen

Deze repo heet **ratatoskr**. De app heet **Ratatoskr** — in de Noorse mythe
de eekhoorn die boodschappen op en neer draagt langs de wereldboom, tussen de
adelaar in de kroon en de slang bij de wortels. Dat is letterlijk wat deze laag
doet: berichten dragen tussen de mens en de vloot.

De boom zelf is het geheel — relay, habitat, handbook, zettelkast — en die heet
**Yggdrasil**. Let op: *Yggdrasil Network* (`yggdrasil-network/yggdrasil-go`) is
een bestaand, bekend overlay-netwerkproject in precies onze buurt. De naam past
daarom bij het ecosysteem als verhaal, niet als productnaam van een component;
zie de sessie-analyse in `#architectuur` (2026-09-11) voor waarom we hun techniek
ook niet lenen.

Sinds 2026-09-11 volgt de techniek de naam: repo `MWest2020/ratatoskr`, image
`ghcr.io/mwest2020/ratatoskr-chat`, volume `ratatoskr-chat-data`, instellingen
`RATATOSKR_*`. De oude namen blijven werken waar het telt — `BOOMHUIS_*` wordt
nog gelezen als terugval, en het pakket `boomhuis-chat` blijft staan omdat
installaties daarop gepind kunnen zijn. De relay heet nog steeds `buzz`: dat is
software van iemand anders.
