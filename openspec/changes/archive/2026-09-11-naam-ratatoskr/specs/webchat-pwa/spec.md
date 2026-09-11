# webchat-pwa

## ADDED Requirements

### Requirement: Instellingen heten RATATOSKR_, en de oude naam blijft werken

Elke instelling die de chat uit de omgeving leest SHALL primair onder
`RATATOSKR_<naam>` gelezen worden, en SHALL terugvallen op `BOOMHUIS_<naam>`
wanneer de eerste ontbreekt. Het lezen SHALL via één gedeelde functie lopen, zodat
er geen leesplek kan achterblijven bij een volgende hernoeming.

De terugval SHALL niet stilzwijgend verdwijnen zolang er installaties bestaan die
de oude naam gebruiken: hij is de enige weg terug na een mislukte uitrol.

#### Scenario: Nieuwe installatie

- **WHEN** alleen `RATATOSKR_URL` gezet is
- **THEN** gebruikt de app die waarde

#### Scenario: Draaiende installatie tijdens de hernoeming

- **WHEN** een nieuw image start tegen een `.env` die nog `BOOMHUIS_URL` heeft
- **THEN** werkt de installatie ongewijzigd door

#### Scenario: Beide gezet

- **WHEN** zowel `RATATOSKR_URL` als `BOOMHUIS_URL` gezet zijn
- **THEN** wint `RATATOSKR_URL`
