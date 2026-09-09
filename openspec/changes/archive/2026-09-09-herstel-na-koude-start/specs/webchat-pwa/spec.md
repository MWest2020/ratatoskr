## ADDED Requirements

### Requirement: De app herstelt zelf zodra het netwerk terug is

De webchat SHALL blijven proberen zijn gegevens te laden wanneer de eerste
poging faalt, en SHALL zich herstellen zonder handmatige herlaad zodra het
netwerk antwoordt. Een mislukte eerste laadpoging SHALL de poll-timer en de
luisteraars van de app niet verhinderen; die worden gezet vóór de eerste
netwerkaanroep.

Zolang er geen verbinding is SHALL de app dat tonen in plaats van een
laad-indicator te laten staan — een scherm dat "laden…" blijft zeggen is niet
te onderscheiden van een kapotte app.

#### Scenario: Koude start vóór de tunnel op is

- **WHEN** de app start terwijl de API onbereikbaar is (de service worker
  serveert de gecachete shell) en het netwerk daarna alsnog beschikbaar komt
- **THEN** laadt de app zijn kanalen en berichten alsnog, zonder herlaad

#### Scenario: Geen verbinding is zichtbaar

- **WHEN** de app zijn gegevens niet kan laden
- **THEN** meldt hij dat er geen verbinding is en dat het opnieuw geprobeerd
  wordt, in plaats van een laad-indicator te laten staan
