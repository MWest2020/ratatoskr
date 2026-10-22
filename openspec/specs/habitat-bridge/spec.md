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
