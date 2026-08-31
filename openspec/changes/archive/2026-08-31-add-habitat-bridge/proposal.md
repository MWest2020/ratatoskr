## Why

Fase 0–2 maken de relay een spiegel (habitat → buzz) en zetten chat-agents in de
kanalen. De omgekeerde richting is de laatste stap naar Marks eindbeeld — *"doel
definiëren, de agents doen de rest"*: een doel in `#bouw` dat (na Marks
bevestiging) tot een habitat-run leidt, en reviewer-/security-findings die als
thread-reply terugkomen zodat de herstelronde ("max 2 herstelrondes" uit het
orchestrator-mandaat) eindelijk een mechanisme heeft. Bewust de láátste fase: hij
raakt habitats hardste invariant en steunt op bewezen fase-0/1/2-betrouwbaarheid.

De kooi-kant is nu opgelost zónder de kooi te verzwakken: de habitat-change
`amend-worker-task-ref` (proposal-first in habitat) staat een optionele
git-pad-taakreferentie toe — de worker blijft doof voor alles buiten env + git.
Deze boomhuis-change bouwt daarop voort.

## What Changes

Twee delen, oplopend in risico:

- **Deel A — findings-terug (uitgaand, geen kooi-amendement nodig).** De
  gestructureerde reviewer-/security-findings uit een run (`worker/schemas/*.json`)
  worden orchestrator-zijde als thread-reply onder de run-post in `#runs`/`#review`
  gepost. Nu een doodlopende steeg; hierna heeft een herstelronde een adres.
- **Deel B — kanaal → dispatch (Mark poortwachter).** Een verzoek/mention in
  `#bouw` leidt tot een **dispatch-voorstel** dat de orchestrator in de thread
  zet; **niets dispatcht autonoom**. Ná Marks expliciete bevestiging schrijft de
  orchestrator het taak/plan-bestand in de doelrepo (git, gecommit), en roept
  `dispatch.sh` aan met `HABITAT_TASK_REF` naar dat pad. Vergt
  `amend-worker-task-ref` (habitat) toegepast.

## Capabilities

### New Capabilities

- `habitat-bridge`: de tweerichtingskoppeling kanaal ↔ dispatch, met Mark als
  poortwachter en git als transport.

### Modified Capabilities

<!-- Habitats worker-execution-amendement is een aparte change in habitat
     (amend-worker-task-ref), proposal-first aldaar — niet hier. -->

## Impact

- **Deel A** is orchestrator-zijde, buiten de kooi — te bouwen zodra fase 1 loopt.
- **Deel B** hangt af van `amend-worker-task-ref` (habitat) én raakt het
  orchestrator-mandaat (elke kanaal-dispatch is een merge-achtige actie → Mark
  bevestigt). Verdicts en audit blijven git-native; de brug is gemak, geen gezag.
- Chat-agents blijven conversatie-only: zij stéllen voor, de orchestrator (buiten
  de kooi) dispatcht na Marks go. Geen agent roept `dispatch.sh` aan.
