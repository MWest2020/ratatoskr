# recurring-jobs

## ADDED Requirements

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
