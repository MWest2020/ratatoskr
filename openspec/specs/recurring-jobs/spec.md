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

### Requirement: Dagelijkse zettelkast-terugkoppeling

Het boomhuis SHALL dagelijks in `#news_from_zettelkast` melden wat er die dag met
Marks gedeelde clips is gebeurd: wat er gecaptured is, wat er nog openstaat, en
wat daarmee zou moeten gebeuren. De job SHALL ná de capture-run van de zettelkast
draaien en SHALL best-effort zijn (leeg of gefaald antwoord post niets en laat
niets falen).

De context SHALL onderscheid maken tussen een bron die nog nergens verwerkt is en
een clip waarvan de fetch-snapshot al gecaptured is; die laatste is afgehandeld,
ook al citeert geen enkele wiki-pagina het clipbestand zelf. Zonder dat
onderscheid rapporteert de job elke dag dezelfde achterstand die er geen is.

#### Scenario: Clip verwerkt

- **WHEN** de capture-run die ochtend een clip tot wiki-pagina heeft gemaakt
- **THEN** staat die in de melding, met de pagina erbij

#### Scenario: Reeds afgehandelde clip

- **WHEN** een clip ongeciteerd is maar zijn fetch-snapshot in `wiki/log.md` staat
- **THEN** telt hij niet als achterstand

#### Scenario: Zettelkast onbereikbaar

- **WHEN** de context niet gelezen kan worden
- **THEN** meldt de job dat als LEESFOUT en niet als "niets te doen"
