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

### Requirement: Issues of an archived change close by themselves

On a periodic tick the listener SHALL, for each open issue titled `build: <change>` or `propose: <change>`, read `openspec/changes` and `openspec/changes/archive` on that issue's repository, and SHALL close the issue only when the change id is absent from `openspec/changes` and exactly one archive directory `YYYY-MM-DD-<id>` exists. The detection SHALL be stateless: it SHALL read main itself and keep no snapshot. Each close SHALL carry a comment with the archive path as pointer, posted before the close. Only repositories with an open build issue SHALL be polled, at most one pair of listing calls per repository per tick. A change that is absent from `openspec/changes` without an archive directory SHALL NOT be closed, only logged. On a `gh` error or rate limit the listener SHALL skip the tick for that repository and log the reason. Issues that are already closed SHALL NOT be touched. A close that fails SHALL be logged with its reason.

#### Scenario: A change is archived

- **WHEN** a change is archived and an open `build: <change>` and an open `propose: <change>` issue exist
- **THEN** both are commented with the archive path and closed

#### Scenario: A change is removed without archive

- **WHEN** a change is absent from `openspec/changes` and no archive directory exists for it
- **THEN** its issues stay open and the listener logs that the change left main without an archive

#### Scenario: A change is still on main

- **WHEN** the change is still in `openspec/changes`
- **THEN** its issues are left alone

#### Scenario: Nothing open is left alone

- **WHEN** the change has no open `build:` or `propose:` issue, or the closer runs a second time
- **THEN** no issue is closed and no comment is posted

#### Scenario: The listener restarts with empty state

- **WHEN** the listener starts with no stored state and a change is already archived on main
- **THEN** the next tick closes its open issues with the archive path

#### Scenario: gh fails or is rate limited

- **WHEN** reading the listing from main fails
- **THEN** nothing is closed for that repository, and the reason is logged

#### Scenario: A close fails

- **WHEN** `gh` refuses to close an issue
- **THEN** the listener logs which issue and why, and carries on with the others
