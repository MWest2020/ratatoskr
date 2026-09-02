## ADDED Requirements

### Requirement: Uitkomsten naar het passende kanaal

De ping-helper SHALL een bericht naar een gekozen kanaal kunnen sturen (niet alleen
#general), zodat uitkomsten in het juiste kanaal landen — review-verdicts in
#review, build-run-uitkomsten in #runs.

#### Scenario: Review-verdict naar #review

- **WHEN** een review-uitkomst wordt gepost via de ping-helper met kanaal `review`
- **THEN** verschijnt het verdict in #review (ondertekend door de reviewer-identiteit),
  niet in #general
