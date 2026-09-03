# recurring-jobs Specification

## Purpose
TBD - created by archiving change add-standup-jobs. Update Purpose after archive.
## Requirements
### Requirement: Dagelijkse standup- en gedaan-digest

Het boomhuis SHALL dagelijks twee digests naar #standup posten via het `jobs/`-mechanisme (naast de bestaande recurring jobs news_from_zettelkast/proposals/technical_debt): een **standup** om 08:00 (open werk + blokkades) en een **gedaan**-terugblik om 18:00 (wat vandaag af is). Beide SHALL best-effort zijn
(een leeg of gefaald `claude -p`-antwoord post niets en laat niets falen) en SHALL
alleen samenvattingen/metadata bevatten, nooit secrets. De **standup**-timer SHALL
`Persistent=true` zijn (een gemiste run haalt bij boot in en toont dán de actuele
open stand — nog steeds bruikbaar); de **gedaan**-timer SHALL `Persistent=false`
zijn, want die is datum-relatief — een catch-up zou de verkeerde (nieuwe) dag
rapporteren, dus een gemiste terugblik wordt overgeslagen i.p.v. misleidend
ingehaald.

#### Scenario: Ochtend-standup

- **WHEN** de standup-timer om 08:00 vuurt
- **THEN** verschijnt in #standup een korte lijst van open PR's/OpenSpec-changes,
  recente #escalatie/#review-signalen en blokkades, en blokkeert het genereren niets

#### Scenario: Stille dag (best-effort)

- **WHEN** er die dag niets is gebeurd; de **gedaan**-prompt vraagt het model om
  een leeg antwoord (de standup heeft altijd blokkade-context)
- **THEN** post `run-job.py` niets bij een leeg stdout — dit is best-effort
  (LLM-compliance), geen harde guard; een korte "niks noemenswaardigs" is een
  aanvaardbare uitkomst

#### Scenario: Gemiste gedaan-run

- **WHEN** de host om 18:00 uit staat en pas de volgende dag boot
- **THEN** wordt de gemiste gedaan-terugblik overgeslagen (Persistent=false), zodat
  er geen terugblik met de verkeerde dag verschijnt

