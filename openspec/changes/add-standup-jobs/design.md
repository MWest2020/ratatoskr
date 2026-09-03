# Design: add-standup-jobs

## Post-identiteit: orchestrator, niet coordinator

Inhoudelijk zou "waar lopen we vast" bij de coordinator passen, maar een job-post
vereist dat de identiteit lid is van het kanaal, en kanaal-lidmaatschap toevoegen
wordt door de auto-mode-classifier geblokkeerd. De orchestrator maakte #standup
aan en is dus al eigenaar/lid — daarom post orchestrator. De coördinator-stem zit
in de prompt, niet in de afzender.

## Dagelijks 08:00 / 18:00

Marks expliciete cadans: 08:00 een reminder van open werk + blokkades (de dag
starten met overzicht), 18:00 een terugblik op wat af is. `OnCalendar=*-*-* HH:00`,
`Persistent=true` voor **standup** (een gemiste ochtend-run haalt bij boot in en
toont dán de actuele open stand). **gedaan** is bewust `Persistent=false`: die is
datum-relatief, dus een catch-up de volgende dag zou de verkeerde (nieuwe) dag
rapporteren — een gemiste terugblik slaan we liever over dan misleidend in te halen.
De gedaan-context leest lokale clones (`git log --all`, geen fetch) — best-effort;
de merged-PR-search vangt remote merges deels op.

## Timers in de repo, niet host-only

De bestaande job-timers leven alleen op de host (`~/.config/systemd/user/`) — niet
reproduceerbaar uit git. Deze change commit de twee nieuwe timers in
`jobs/systemd/` (boring/auditable); het retro-committen van de bestaande timers is
bewust buiten scope.

## Best-effort erft van het jobs-mechanisme

`run-job.py` post niets bij een leeg `claude -p`-antwoord en laat niets falen. De
"stille dag = geen ruis" is best-effort: de prompt vraagt het model om leeg te
antwoorden op een lege context — LLM-compliance, geen deterministische guard. Een
korte "niks noemenswaardigs" is een aanvaardbare uitkomst i.p.v. een valse melding.
Een LEESFOUT in de standup-context (relay/gh weg) wordt expliciet als zodanig
gemarkeerd, zodat een storing nooit als "geen blokkades" leest.
