## ADDED Requirements

### Requirement: Ongelezen-teller per kanaal

De PWA SHALL per kanaal tonen hoeveel berichten er nieuw zijn sinds de gebruiker
dat kanaal op dít apparaat het laatst bekeek, en het openen van een kanaal SHALL
het als gelezen markeren. De telling per apparaat SHALL geen serverstate vereisen
(client-side onthouden), zodat er geen gedeelde "gelezen"-status tussen apparaten
ontstaat.

#### Scenario: Nieuw bericht geeft een badge

- **WHEN** er een bericht in een kanaal verschijnt dat de gebruiker sinds
  aankomst nog niet heeft bekeken
- **THEN** toont de kanaallijst een ongelezen-teller bij dat kanaal

#### Scenario: Openen markeert gelezen

- **WHEN** de gebruiker het kanaal opent
- **THEN** verdwijnt de ongelezen-teller voor dat kanaal op dit apparaat
