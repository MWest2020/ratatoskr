## Why

Fase 1 maakt de relay een spiegel (habitat → buzz). De omgekeerde richting —
een verzoek in `#bouw` dat tot een dispatch leidt, en reviewer-bevindingen die
als thread-reply terugkomen zodat de herstelronde ("max 2 herstelrondes" uit het
orchestrator-mandaat) eindelijk een mechanisme heeft — is de laatste stap naar
de one-man army. Dit is bewust de láátste fase: hij raakt habitats hardste
invariant en verdient maanden bewezen fase-0/1/2-betrouwbaarheid als fundament.

## What Changes (schets — vergt conversational design vóór propose-afronding)

- **Kanaal → dispatch**: een verzoek of mention in `#bouw` leidt tot een
  dispatch-voorstel dat Mark bevestigt; de orchestrator blijft de enige die
  `dispatch.sh` aanroept. Geen autonome dispatch vanuit een bericht.
- **Bevindingen terug**: reviewer-/security-findings (nu al gestructureerd in
  `worker/schemas/*.json`, maar een doodlopende steeg) als thread-reply onder de
  run-post, zodat een herstelronde een adres heeft.
- **Eventueel** een taak-referentie de kooi in: niet via een socket maar als
  git-ref (`HABITAT_TASK_REF` naar een taakbestand), zodat de worker doof
  blijft voor alles buiten env + git.

## Capabilities

### New Capabilities

- `habitat-bridge`: de tweerichtingskoppeling kanaal ↔ dispatch, met Mark als
  poortwachter.

### Modified Capabilities

- Habitats `worker-execution`-spec ("geen andere invoerkanalen") vergt bij een
  taak-referentie een amendement — dat amendement is een OpenSpec-change **in
  habitat**, proposal-first aldaar, en hoort niet stiekem hier te gebeuren.

## Impact

- Raakt het orchestrator-mandaat (habitat) en mogelijk `entrypoint.sh`.
- Verdicts en audit blijven onverkort git-native; de brug is gemak, geen
  gezag.
- Blokkerend: eerst conversational design met Mark; deze proposal is een
  plaatshouder met richting, geen goedgekeurd ontwerp.
