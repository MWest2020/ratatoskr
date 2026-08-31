## ADDED Requirements

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
