## Why

De web-chat maakt kanalen aan ondertekend als `mark` (de mens), dus kanalen als
#red-team/#wordsworth/#netnl/#technical_debt zijn **mens-owned**. Alleen de eigenaar
mag een kanaal beheren (beschrijving, topic, delete), dus geautomatiseerd
kanaalbeheer zou marks mens-sleutel gebruiken — impersonatie-adjacent, en het
maakt de mens nodig voor iets dat een agent hoort te doen. Gevonden bij
add-channel-descriptions (het description-script kan mens-owned kanalen niet zetten).

## What Changes

- **`chat/server.py` `/api/channels/create` tekent voortaan als `orchestrator`**
  (een agent) i.p.v. als `mark`, zodat nieuwe kanalen agent-owned zijn.
- **Her-eigenaar de bestaande mens-owned kanalen** naar orchestrator (via een
  eenmalige, gedocumenteerde stap; afhankelijk van wat de relay aan
  ownership-overdracht ondersteunt — anders recreëren als orchestrator).
- Daarna kan `orchestrator/set-channel-descriptions.py` álle kanalen zetten zonder
  marks sleutel.
