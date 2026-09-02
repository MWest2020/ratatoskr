## ADDED Requirements

### Requirement: Kanalen dragen een reproduceerbare beschrijving

Elk vast kanaal SHALL een native relay-beschrijving hebben die overeenkomt met zijn
`doel` in `channels.yml`, gezet via een reproduceerbaar script
(`orchestrator/set-channel-descriptions.py`) i.p.v. een eenmalige handmatige stap.

#### Scenario: Beschrijving reproduceerbaar (her)zetten

- **WHEN** een `doel` in channels.yml wijzigt of de relay is hersteld
- **THEN** zet het script de beschrijving opnieuw op elk kanaal (als eigenaar),
  zodat de beschrijving die de app toont overeenkomt met channels.yml
