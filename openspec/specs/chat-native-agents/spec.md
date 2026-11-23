# chat-native-agents Specification

## Purpose

De tweede agentklasse: agenten die in de chat leven in plaats van in een
habitat-kooi, en de grenzen die dat verschil nodig heeft.

Een habitat-worker is een Job met een begin en een eind; een chat-native agent
luistert en antwoordt. Dat verschil verplaatst het risico maar haalt het niet
weg, dus gelden hier eigen varianten van dezelfde regels: het mandaat ligt buiten
het bereik van de agent, het bestaan is begrensd, model en gereedschap komen uit
de registry in plaats van uit een prompt, en de audit-lat is dezelfde.

## Requirements

### Requirement: Tweede agentklasse met eigen kooi-principes

Chat-native agents SHALL langlopend draaien via `buzz-acp` met een eigen
keypair uit de registry, op een eigen host buiten de habitat-namespace, zonder
git-push-credentials; hun deliverable is tekst in kanalen.

#### Scenario: Uitkomst wil code worden

- **WHEN** een gesprek uitmondt in een gewenste codewijziging
- **THEN** ontstaat die via een OpenSpec-change en een habitat-run, nooit
  doordat de chat-agent zelf ergens pusht

### Requirement: Mandaat buiten bereik van de agent

Het mandaat van elke chat-native agent SHALL in de boomhuis-repo leven en voor de
agent zelf niet wijzigbaar zijn; een agent die zijn mandaat, sleutels of
relay-configuratie kan aanpassen is een harde fout.

#### Scenario: Poging tot zelfverbouwing

- **WHEN** een agent probeert zijn mandaat of configuratie te wijzigen
- **THEN** faalt dat aantoonbaar en wordt het als incident geëscaleerd

### Requirement: Begrensd bestaan

Elke chat-native agent SHALL een idle-timeout (automatische reaping) en een
budgetplafond hebben; overschrijding SHALL de agent stoppen en escaleren, niet
stilzwijgend doorbranden.

#### Scenario: Nachtrust

- **WHEN** een agent de idle-timeout bereikt
- **THEN** draint hij lopende beurten, publiceert offline-presence en stopt

### Requirement: Zelfde audit-lat als de kooi

Elk agent-bericht SHALL via de Nostr-signatuur herleidbaar zijn tot de
rol-identiteit, en het relay-log SHALL doorzoekbaar zijn; anonieme of geleende
identiteiten bestaan niet.

#### Scenario: Wie zei dit

- **WHEN** later de vraag rijst welke agent een uitspraak deed
- **THEN** geeft de signatuur + registry daar eenduidig antwoord op

### Requirement: Listener routeert op relay-lidmaatschap

De listener SHALL een chat-agent laten reageren op een `@handle`-mention in kanaal C
wanneer de agent handbook-gescopt is op C (`chat.channels`) OF relay-LID is van C.
Relay-lidmaatschap is een additieve reden om te reageren; het VERVANGT de handbook-
scope niet. Zo wordt een agent die lid wordt (via de webchat-pop-up, de hub-
default, of de operator-backfill) daadwerkelijk aanspreekbaar zonder handbook-wijziging.

Alleen de MENTION-tak wordt zo verbreed. Het thread-vervolg (de laatst-actieve agent
praat door ZONDER nieuwe mention) SHALL def-kanaal-only blijven: relay-lidmaatschap
maakt een agent aanspreekbaar op expliciete mentions, maar laat 'm niet ongevraagd
meepraten in een kanaal dat niet in z'n handbook-`chat.channels` staat.

De listener SHALL de te pollen kanaal-set live uit de relay bepalen (`buzz channels
list`), met `channels.yml` als vangnet, zodat na deploy aangemaakte kanalen worden
opgepikt. Kanaal-lidmaatschap en kanaal-lijst MOGEN kort gecachet worden; een
MISLUKTE fetch SHALL een eerder geslaagde cache niet overschrijven. Voor de kanaal-
LIJST geldt een geslaagd-maar-lege uitkomst óók als mislukt (een lege lijst is nooit
legitiem). Voor LIDMAATSCHAP is een geslaagde lege uitkomst wél geldig (het laatste
lid kan weg zijn) en actualiseert die de cache.

#### Scenario: Lid-maar-niet-def-gescopt reageert

- **WHEN** een agent relay-lid is van een kanaal dat niet in z'n handbook-
  `chat.channels` staat, en daar `@agent` wordt genoemd
- **THEN** reageert de agent in dat kanaal

#### Scenario: Def-scope blijft werken

- **WHEN** een agent handbook-gescopt is op een kanaal
- **THEN** reageert de agent daar op een `@agent`-mention, ook als de relay-
  lidmaatschapscall (tijdelijk) niets oplevert

#### Scenario: Nieuw kanaal wordt gepoll'd

- **WHEN** een kanaal via de webchat is aangemaakt en dus niet in `channels.yml` staat
- **THEN** neemt de listener het via de live kanaal-lijst op in de poll-set

#### Scenario: Vervolg zonder mention blijft def-kanaal-only

- **WHEN** een agent alléén via relay-lidmaatschap (niet via z'n handbook-
  `chat.channels`) in een kanaal zit en er een bericht ZONDER mention op z'n
  vorige beurt volgt
- **THEN** praat de agent NIET automatisch door — het thread-vervolg geldt alleen
  in de handbook-gescopte kanalen

### Requirement: Model en tools uit de registry worden afgedwongen

De listener SHALL het model en de toolgrenzen uit de handbook-definitie meegeven
aan elke beurt (`--model`, `--allowedTools`, `--disallowedTools`), en SHALL een
agent zonder `model` in zijn definitie **niet** spawnen. Een gedeclareerde grens
die niet wordt meegegeven is geen grens; een ontbrekend model laat de agent stil
op de omgevingsdefault draaien.

#### Scenario: Geweigerde tool voert niets uit

- **WHEN** een agent gevraagd wordt een tool te gebruiken die zijn definitie
  weigert
- **THEN** gebeurt de actie niet en meldt de agent dat hij die tool niet heeft

#### Scenario: Definitie zonder model draait niet

- **WHEN** een definitie in de registry geen `model` declareert
- **THEN** wordt die agent niet gespawnd, met de reden in het listener-log

### Requirement: Limitaties en statistiek per beurt gemeld

Elke beurt SHALL één regel statistiek opleveren in `#statistics` (agent, kanaal,
gedraaid model, turns, kosten). Loopt een beurt tegen een grens — een geweigerde
tool, een storing, of een door de agent zelf gemelde limitatie — dan SHALL er
**één** geaggregeerde melding per beurt naar `#escalatie` gaan, zodat een mens
beslist of de rol verruimd wordt. Melden SHALL nooit de beurt zelf laten falen.

#### Scenario: Eén melding per beurt, niet per aanroep

- **WHEN** een beurt meerdere keren tegen dezelfde grens loopt
- **THEN** verschijnt er één melding in `#escalatie` die de grenzen samenvat

#### Scenario: Zelfrapportage vult wat de runtime niet ziet

- **WHEN** een tool niet is toegestaan en daardoor niet eens wordt aangeboden —
  er is dan geen geweigerde aanroep om te registreren
- **THEN** meldt de agent de limitatie zelf in een machineleesbare regel en tilt
  de listener die naar `#escalatie`

#### Scenario: Een kapotte melding kost geen antwoord

- **WHEN** het posten van statistiek of escalatie faalt
- **THEN** is het antwoord in het kanaal al verstuurd en blijft de listener draaien

### Requirement: Waar een agent naartoe mag staat in zijn definitie

De kanalen waar een agent naartoe mag doorsturen SHALL uit de
handbook-definitie komen (`agent.chat.routes`). Een ontbrekend, leeg of
niet-lijstvormig veld SHALL betekenen dat de agent niets mag doorsturen, en de
listener SHALL dat recht niet uit een prompt, een lokale configuratie of een
eerdere beurt afleiden.

#### Scenario: Geen routes in de definitie

- **WHEN** een agent zonder `routes` een `!route`-marker schrijft
- **THEN** gaat er niets weg en meldt de listener de weigering in #escalatie

#### Scenario: Een kanaal buiten de lijst

- **GIVEN** een agent met `routes: [bouw]`
- **WHEN** hij naar #general wil doorsturen
- **THEN** gaat er niets weg en noemt de weigering welke kanalen wél mogen

### Requirement: Een agent stuurt een bestaand bericht door, met eventueel eigen duiding

Een chat-native agent SHALL een bestaand bericht uit het huidige kanaal kunnen
doorsturen naar een ander kanaal via een `!forward #<kanaal> <bericht-id>`-marker
in zijn antwoord. De listener SHALL de inhoud zelf uit het kanaal ophalen; de
agent SHALL die inhoud niet aanleveren, zodat een verzonnen citaat onmogelijk is
in plaats van alleen verboden.

Een agent MAY een eigen notitie meesturen. Die SHALL onder het citaat staan en
SHALL de naam van de doorstuurder dragen, zodat een lezer haar niet voor het
origineel aanziet.

De listener SHALL aan elk doorgestuurd bericht een bronvermelding toevoegen met
de oorspronkelijke schrijver, het bronkanaal en het bericht-id, en die vermelding
SHALL niet door de agent te schrijven, te wijzigen of weg te laten zijn.

De doelkanalen SHALL uit de handbook-definitie komen (`agent.chat.routes`); een
ontbrekend, leeg of niet-lijstvormig veld SHALL betekenen dat de agent niets mag
doorsturen. Wijst de agent niet eenduidig één bestaand bericht aan, dan SHALL er
niets doorgestuurd worden en SHALL de weigering met reden in #escalatie
verschijnen.

#### Scenario: Een bericht doorgeven met duiding

- **GIVEN** een bericht van mark in #architectuur met id `aaaa1111…`
- **WHEN** odin antwoordt met `!forward #bouw aaaa1111` gevolgd door een eigen notitie
- **THEN** verschijnt in #bouw de inhoud van dát bericht in een blockquote, met
  een bronvermelding die mark, #architectuur en het id noemt, en daaronder de
  notitie onder odins naam

#### Scenario: Een verzonnen id stuurt niets

- **WHEN** odin een bericht-id noemt dat niet in dit kanaal bestaat, of een
  voorvoegsel dat op meerdere berichten past
- **THEN** wordt er niets geplaatst en verschijnt de weigering met reden in
  #escalatie en in het bronkanaal

#### Scenario: Een kanaal buiten het mandaat

- **GIVEN** een agent met `routes: [bouw]`
- **WHEN** hij naar #general wil doorsturen
- **THEN** gaat er niets weg en noemt de weigering welke kanalen wél mogen

### Requirement: Een agent weet wat hij kan, uit zijn eigen definitie

De listener SHALL een agent in zijn systeemprompt vertellen welke mogelijkheden
hij heeft, gegenereerd uit zijn eigen definitie en niet uit losse prompttekst.
Een mogelijkheid die alleen elders in de handbook-definitie beschreven staat
SHALL niet als bekend gelden: `fetch_def` leest de systeemprompt uitsluitend uit
het blockquote onder `## Chat-facet`.

Waar een mogelijkheid gegevens uit het gesprek nodig heeft — zoals een bericht-id
om naar te wijzen — SHALL de prompt die gegevens dragen, en SHALL dat achterwege
blijven bij een agent die de mogelijkheid niet heeft.

#### Scenario: Geen rechten, geen aankondiging

- **GIVEN** een agent zonder `routes` in zijn definitie
- **WHEN** de listener zijn systeemprompt opbouwt
- **THEN** staat er geen doorstuur-instructie in, en dragen de berichten in de
  prompt geen id

#### Scenario: Wel rechten, dus ook het gereedschap om te wijzen

- **GIVEN** een agent met `routes: [bouw]`
- **THEN** noemt zijn systeemprompt `!forward` en alleen #bouw, en dragen de
  berichten in de prompt hun korte id

### Requirement: Een kanaal mag een standaard-agent noemen

Een kanaal SHALL in `channels.yml` een `default_agent` kunnen noemen. Een
menselijk bericht zonder vermelding en zonder vervolgdoel SHALL dan naar
die agent gaan. Dat is opt-in per kanaal: zonder `default_agent` SHALL een
kanaal zich gedragen zoals voorheen.

De volgorde van de drie triggers is het contract en SHALL vastliggen:
een **vermelding** gaat vóór een **vervolg**, en een vervolg gaat vóór de
**standaard-agent**. Voor het vervolg SHALL alleen de meest recente agent in
de laatste tien berichten tellen; mensen daartussen breken het niet. Mag
die agent hier niet vervolgen — hij antwoordde op een vermelding via
relay-lidmaatschap — dan is er niets te vervolgen en SHALL het bericht
als koude start gelden: de standaard-agent antwoordt. Stilte zou er
precies uitzien als een listener die niet draait. Bij elke beurt SHALL de reden noemen welke regel
afging, zodat een log een lopend gesprek kan onderscheiden van een koude
start.

Alles wat al gold, blijft gelden: een agent SHALL nooit op een andere agent
antwoorden, een markeringsregel (`!sessie`, `!route`) SHALL via zijn eigen
pad lopen, en een agent SHALL alleen spreken waar zijn definitie en het
relay-lidmaatschap dat toestaan.

De listener SHALL weigeren te starten als een kanaal een standaard-agent
noemt die in dat kanaal niet mag spreken — liever niet opstarten dan
stilzwijgend nooit antwoorden.

#### Scenario: Koude start gaat naar de standaard-agent

- **GIVEN** `#general` met `default_agent: odin`
- **WHEN** een mens een bericht zonder vermelding plaatst en er geen agent
  in de laatste tien berichten sprak
- **THEN** odin antwoordt, en de reden in het log noemt de standaardregel

#### Scenario: Een vermelding gaat voor de standaard

- **GIVEN** `#general` met `default_agent: odin`
- **WHEN** een mens `@architect` vermeldt
- **THEN** architect antwoordt, niet odin

#### Scenario: Een lopend gesprek gaat voor de standaard

- **GIVEN** `#general` met `default_agent: odin`, en architect — wiens
  definitie `#general` noemt — sprak drie berichten geleden
- **WHEN** een mens zonder vermelding reageert, ook als er intussen een
  ander mens iets zei
- **THEN** architect antwoordt als vervolg, niet odin

#### Scenario: Een recente agent die hier niet mag vervolgen, geeft de beurt aan de standaard

- **GIVEN** `#general` met `default_agent: odin`, en architect — wiens
  definitie `#general` niet noemt — antwoordde net op een vermelding
- **WHEN** een mens zonder vermelding reageert
- **THEN** antwoordt odin, met reden `default`

#### Scenario: Buiten het venster valt het vervolg weg

- **GIVEN** `#general` met `default_agent: odin`, en architect sprak meer
  dan tien berichten geleden
- **WHEN** een mens zonder vermelding iets zegt
- **THEN** odin antwoordt, want er is geen vervolgdoel meer

#### Scenario: Een kanaal zonder standaard blijft stil bij een koude start

- **GIVEN** `#statistics` zonder `default_agent`
- **WHEN** een mens zonder vermelding iets zegt en er geen vervolgdoel is
- **THEN** antwoordt er niemand

#### Scenario: Een standaard die niet mag spreken, houdt de start tegen

- **GIVEN** `channels.yml` noemt als `default_agent` een agent wiens
  definitie dat kanaal niet toestaat
- **WHEN** de listener opstart
- **THEN** weigert hij te starten en noemt hij kanaal en agent

### Requirement: A reply addresses the agent it replies to

When a human's message replies to an agent's message in the same channel, the
listener SHALL treat that agent as addressed, as an @mention does, within the
agent's channel scope. An explicit @mention SHALL take precedence. In a shared
room, a reply SHALL continue the issue referenced by the parent message.

#### Scenario: A reply without @

- **WHEN** Mark replies "go ahead" to bouwer's message in #bouw, without an @
- **THEN** bouwer answers, as if Mark had written "@bouwer go ahead"

#### Scenario: A reply in the room

- **WHEN** Mark replies to architect's message ending `· ratatoskr#57` in
  #werkplaats while #58 is the room's latest issue
- **THEN** the message is recorded on ratatoskr#57 and architect answers

### Requirement: A chat agent can read the state of the work through a bounded read shell

A chat agent whose handbook definition allows exactly
`Bash(python3 agents/readshell.py:*)` SHALL be able to run the read shell. The
read shell answers six read-only questions about a repository of `MWest2020`:
recent commits, branches, open OpenSpec changes, open PRs, open issues and the
checks of a PR.

The read shell SHALL:

- fix the owner;
- validate the repository name, numbers and labels before running anything;
- run each question as one fixed argument list without a shell;
- report a failure with its reason instead of empty output.

The listener SHALL tell the agent about the read shell in its system prompt,
generated from the definition, and say nothing when the definition does not
allow it.

#### Scenario: Odin reads the open PRs of a repository

- **WHEN** a definition allows the read-shell rule and the agent runs
  `python3 agents/readshell.py prs wordsworth`
- **THEN** it gets the open PRs of `MWest2020/wordsworth`, at most 40 lines

#### Scenario: Another owner or a crafted name is refused

- **WHEN** the agent passes `other/repo`, `../x` or `-x` as the repository
- **THEN** the read shell refuses it with a reason and runs no command

#### Scenario: The agent is not told about a shell it does not have

- **WHEN** a definition does not allow the read-shell rule
- **THEN** its system prompt does not mention the read shell

### Requirement: A chat turn gets no Bash other than the read shell

The listener SHALL NOT spawn a chat agent whose definition allows any Bash
entry other than the exact read-shell rule. It SHALL log the offending entry,
like a definition without a model.

#### Scenario: A free shell in a chat facet is refused

- **WHEN** a chat facet declares `allow: [Read, Bash]`
- **THEN** that agent is not spawned and the listener log names `Bash` as the
  reason

### Requirement: Odin starts a build, and the listener decides whether it runs

The hub MAY end an answer with `!build <repo> <change>`. The listener SHALL run
habitat's chain (architect, builder, reviewer, security) only when four
conditions hold:

- the repository is on the factory's list of Mark's repositories;
- the OpenSpec change exists on that repository's main;
- the work has an issue;
- the daily build budget is not used up.

It SHALL record each role's verdict and branch as a comment on that issue. A
build that does not meet a condition SHALL NOT start, and the listener SHALL
say which condition failed.

#### Scenario: A build without an issue does not start

- **WHEN** odin writes `!build wordsworth some-change` for work that has no
  issue
- **THEN** no Job runs, and the room says the build needs an issue first

#### Scenario: Every verdict is on the issue

- **WHEN** the chain runs for an issue
- **THEN** the issue gets one comment per role with its verdict and branch

### Requirement: A build that passes the cage and CI is merged without Mark

When all four roles pass, the listener SHALL open a pull request from the
builder branch, merge it once every check passes, and close the issue with a
link to the merge. alma SHALL never be a deploy target.

#### Scenario: A red check stops the merge

- **WHEN** one check on the pull request fails
- **THEN** nothing is merged, and the issue says which check failed

### Requirement: Closing is Mark's

Odin MAY create roles and channels. Closing a role or channel, or changing an
existing role's mandate or tools, SHALL only happen after Mark answers the
proposal with `!yes`, from his current pubkey.

#### Scenario: Odin proposes to close a channel

- **WHEN** odin proposes to archive a channel
- **THEN** nothing is archived until Mark answers `!yes`

### Requirement: The hub consults other agents itself

The hub MAY put `!consult <agent>[,<agent>] <question>` on the first line of
its answer. The listener SHALL then give each named agent (at most two;
existing, not the hub, and allowed to speak in that channel) one turn in the
same channel. That turn gets Mark's message and the hub's question, and the
agent answers under its own name. A consulted agent's answer SHALL NOT be read
for `!consult`, so consulting never chains. An agent that is refused SHALL be
named in the channel with the reason.

Added on Mark's decision of 2026-10-23 ("ja, bouw !consult"). Until then odin
had to ask Mark to post its questions to other agents: a `!route`d message is
posted under odin's key, and the loop guard skips agent messages, so nobody
answered it.

#### Scenario: Odin asks architect and reviewer

- **WHEN** odin answers with `!consult architect,reviewer Is this an MVP?`
- **THEN** after odin's answer, architect and then reviewer answer in the same
  channel, each with Mark's message and odin's question

#### Scenario: No chains

- **WHEN** a consulted agent writes `!consult bouwer …` itself
- **THEN** bouwer gets no turn

### Requirement: A decided change gets written without the coding session

The hub MAY put `!propose <repo> <change-id> <summary>` on the first line of
its answer, for a repository on the factory's list. The listener SHALL open an
issue for it, and SHALL start a writing session in a fresh worktree that may
write only under `openspec/changes/<change-id>/`, with `openspec validate` as
its only command. When the session ends, the listener SHALL check that every
changed path is under that directory and that
`openspec validate <change-id> --strict` exits zero. Only then SHALL it commit,
push the session branch and open a pull request. The PR SHALL be merged once
every check passes and SHALL NOT be deployed. After the merge, the hub SHALL
get one follow-up turn to build the change.

#### Scenario: A stray file stops the proposal

- **WHEN** the session also writes a file outside `openspec/changes/<id>/`
- **THEN** no PR is opened, and the issue and the channel say which file

### Requirement: A chat agent runs only with the system prompt from its definition

The listener SHALL take a chat agent's system prompt from the blockquote under
the `## Chat facet` heading of its handbook definition. The heading may be
written with a hyphen or a space, in any case. The listener SHALL NOT spawn an
agent whose prompt comes out empty, and SHALL log the reason, as it does for a
definition without a model.

#### Scenario: The translated heading is found

- **WHEN** a definition has `## Chat facet (ratatoskr · #bouw)` followed by a
  prose line and a blockquote
- **THEN** the system prompt is the blockquote, without the prose line and
  without the next section

#### Scenario: An empty prompt does not run

- **WHEN** a definition has no blockquote under its chat facet
- **THEN** that agent is not spawned and the listener log says
  `no system prompt`

### Requirement: The role contract reaches the model

When a definition has a `## Contract` section, the listener SHALL append that
section to the agent's system prompt, after one instruction line. The line
says: answer only what the contract says you take, and for anything under "Not
mine", name whose it is and stop. A definition without a contract SHALL keep
its prompt unchanged, and a contract SHALL NOT count as a prompt when the chat
facet has none.

#### Scenario: The contract follows the prompt

- **WHEN** a definition has a chat facet with a blockquote and a `## Contract`
  section
- **THEN** the system prompt is the blockquote, then the instruction line, then
  the contract

#### Scenario: No contract, no change

- **WHEN** a definition has no `## Contract` section
- **THEN** its system prompt is exactly the blockquote

### Requirement: In a shared room the role contracts decide who answers

In a channel marked as a shared room, a human message without an @mention SHALL
go to one triage step. The triage step reads the "Takes" and "Not mine" lines
of each room member's contract and names one or more owners with a reason. The
listener SHALL post the outcome as a visible claim line, and only the named
owners SHALL answer. When triage fails or names nobody, the listener SHALL say
so in the room instead of staying silent. An @mention SHALL take precedence
over triage.

#### Scenario: A design question goes to architect

- **WHEN** Mark writes a design question in the shared room without naming an
  agent
- **THEN** the room shows a claim line naming architect and the reason, and
  only architect answers

#### Scenario: Nobody takes it

- **WHEN** triage names no owner
- **THEN** the room shows "nobody took this" with the reason

### Requirement: A hand-off between agents is visible and bounded

An agent in a shared room MAY end its answer with `!handoff <agent> <line>`.
The listener SHALL give the target one turn only when two conditions hold: the
target is a room member, and the target appears in the source agent's contract
under "Hands off to". A human message SHALL cause at most three hand-offs.

#### Scenario: The hop limit holds

- **WHEN** a third hand-off has run for one human message and an agent writes
  a fourth
- **THEN** no turn starts, and the room says the limit was reached
