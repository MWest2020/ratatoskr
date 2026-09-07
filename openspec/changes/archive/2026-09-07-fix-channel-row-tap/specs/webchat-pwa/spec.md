## ADDED Requirements

### Requirement: De hele kanaalrij is het klikdoel

Een rij in de kanaallade SHALL over haar volledige oppervlak het kanaal openen
en de lade sluiten — niet alleen op de tekst. Alleen de verwijderknop in die rij
SHALL een eigen actie houden.

#### Scenario: Tik naast de kanaalnaam

- **WHEN** de gebruiker in de kanaallade tikt op de lege ruimte rechts van een
  kanaalnaam
- **THEN** wisselt de app naar dat kanaal en sluit de lade, zodat de invoerbalk
  weer bereikbaar is
