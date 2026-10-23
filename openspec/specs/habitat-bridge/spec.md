# habitat-bridge Specification

## Purpose

De brug tussen de chat en habitat: wat er nodig is voordat een bericht een
habitat-Job kan worden.

Dit is bewust een korte capability met een hoge drempel. Een chatbericht dat
rechtstreeks werk kan starten is een uitvoerpad dat om de kooi heen loopt, en de
kooi is de enige harde grens die het ecosysteem heeft. Daarom staat hier wie de
poortwachter is en dat er niet gebouwd wordt vóór het amendement op habitats
eigen spec er ligt.

## Requirements

### Requirement: Mark is de poortwachter van de brug

Elke dispatch die uit een kanaalbericht voortkomt SHALL expliciet door Mark
bevestigd worden vóór de orchestrator `dispatch.sh` aanroept; autonome dispatch
vanuit een bericht bestaat niet.

#### Scenario: Verzoek in #bouw

- **WHEN** een bericht in `#bouw` om een bouw-run vraagt
- **THEN** formuleert de orchestrator een dispatch-voorstel in de thread en
  gebeurt er niets tot Mark bevestigt

### Requirement: De brug wordt niet gebouwd vóór het amendement

Er SHALL geen enkele vorm van taak-invoer richting de kooi gebouwd worden
zolang habitats `worker-execution`-spec ("geen andere invoerkanalen") niet via
een OpenSpec-change in de habitat-repo is geamendeerd; bevindingen-terug-in-de-thread
(uitgaand, buiten de kooi) mag wél eerder.

#### Scenario: Verleiding tot een sluiproute

- **WHEN** een taak-referentie de kooi in gewenst is terwijl het amendement in
  habitat nog niet is toegepast
- **THEN** wordt dat werk geweigerd en eerst het amendement proposal-first in
  habitat ingediend

### Requirement: One road from the chat to the cage

There SHALL be exactly one way for a chat message to start a habitat run: the
`!build` marker, which the listener checks (`agents/build.py`). No other script
in the repository SHALL dispatch habitat from a message.

#### Scenario: The old bridge is gone

- **WHEN** someone looks for a way to dispatch habitat from the chat
- **THEN** they find `!build` and its how-to, and no `orchestrator/bridge.py`

### Requirement: A build issue is an issue

When `!build` carries an issue number, the listener SHALL check with `gh` that
the number is an open issue on the repository, not a pull request and not a
closed issue, before the build uses it. When it is not, the listener SHALL open
a fresh build issue, build on that one, and say in the channel that the given
number was not an open issue and which issue is used instead.

#### Scenario: The number is an open issue

- **WHEN** `!build <repo> <change> <number>` is given and `<number>` is an open
  issue on the repository
- **THEN** the build runs on that issue and no new issue is opened

#### Scenario: The number is a pull request

- **WHEN** `!build <repo> <change> <number>` is given and `<number>` is a pull
  request
- **THEN** a fresh build issue is opened, the build runs on it, and the channel
  says the number was not an open issue and names the new one

#### Scenario: The number is a closed issue

- **WHEN** `!build <repo> <change> <number>` is given and `<number>` is a closed
  issue
- **THEN** a fresh build issue is opened, the build runs on it, and the channel
  says so
