## ADDED Requirements

### Requirement: Repos-browser is een sluitbare modal

De Repos-weergave in de PWA SHALL een modale lade zijn met een altijd-zichtbare
sluitknop die vanaf elk niveau (repo-lijst, PR-lijst, PR-detail) terugkeert naar
de chat, naast de niveau-terug-links binnen de lade.

#### Scenario: Sluiten vanaf elk niveau

- **WHEN** de gebruiker de Repos-lade opent en naar een repo of PR navigeert
- **THEN** kan hij met de sluitknop in één tik terug naar de chat, ongeacht het
  niveau waarop hij zich bevindt
