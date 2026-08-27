# Design: add-habitat-bridge

## De stroom (deel B, kanaal → dispatch)

```
#bouw: "@bouwer maak change: statuslijntje in de web-chat"
   │
   ▼ (chat-agent, conversatie-only)
bouwer stelt een OpenSpec-change-vorm voor in de thread (Why/What/Impact)
   │
   ▼ (orchestrator, buiten de kooi, leest de thread)
orchestrator post een DISPATCH-VOORSTEL in de thread:
   "dispatch builder · change=add-chat-statusline · repo=boomhuis — bevestig?"
   │
   ▼ Mark: 👍 (expliciete bevestiging — poortwachter)
orchestrator schrijft het taak/plan-bestand in de DOELREPO (git, commit),
en roept dispatch.sh aan met HABITAT_TASK_REF=<pad>
   │
   ▼ habitat (kooi)
builder-run leest env + git (incl. HABITAT_TASK_REF); pusht branch + verdict
   │
   ▼ (deel A, terug)
findings/verdict als thread-reply onder de run-post in #runs/#review
```

## Waarom Mark poortwachter blijft (niet-onderhandelbaar)

Een dispatch is een merge-achtige, gevolgrijke actie. Het orchestrator-mandaat
(habitat) escaleert al bij elke merge; een dispatch uit een kanaalbericht valt
daar precies onder. Dus: een chat-agent **stelt voor**, de orchestrator
**vertaalt naar een dispatch-voorstel**, en pas Marks expliciete bevestiging
zet `dispatch.sh` in gang. Geen agent en geen bericht dispatcht autonoom. Dit
spiegelt de kooi-filosofie: gevolgrijke acties zijn menselijk-gepoort.

## Waarom git de taak-ref draagt (niet een socket)

De verleiding is een live kanaal de kooi in. Dat sloopt habitats sterkste
invariant ("geen andere invoerkanalen"). In plaats daarvan schrijft de
orchestrator het taakbestand **in de doelrepo** en geeft alleen het **pad** mee
als `HABITAT_TASK_REF` (zie habitat `amend-worker-task-ref`). De worker leest
het uit de gecloonde repo — nog steeds alleen env + git, reproduceerbaar,
auditeerbaar. De brug voegt gemak toe, geen nieuw gezag of nieuw aanvalsoppervlak.

## Verworpen alternatieven

| Optie | Waarom niet |
|---|---|
| Chat-agent roept zelf `dispatch.sh` | Breekt conversatie-only + Mark-poortwachter; agent zou kube-toegang nodig hebben (verboden pad). |
| Live socket/MCP de kooi in | Sloopt "geen andere invoerkanalen"; nieuw aanvalsoppervlak in de egress-allowlist. |
| Autonome dispatch bij een mention | Een dispatch is merge-achtig; moet menselijk-gepoort, net als elke merge. |
| Findings via een centrale store | Onnodig; git + thread-reply is het adres, en blijft git-native. |

## Volgorde

Deel A eerst (uitgaand, geen kooi-amendement, direct waarde: herstelronde krijgt
een adres). Deel B pas ná `amend-worker-task-ref` (habitat) is toegepast en na
bewezen fase-0/1/2-betrouwbaarheid.
