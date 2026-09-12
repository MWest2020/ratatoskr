# relay-deployment

## ADDED Requirements

### Requirement: Eén manier om de chat te draaien

Een installatie SHALL precies één uitrolpad hebben. Na de migratie naar de
compose-stack SHALL het oude pad (systemd-unit plus checkout) verwijderd worden,
zodat er op de machine geen twee manieren naast elkaar staan waarvan niemand
weet welke de echte is.

Het oude pad SHALL pas verdwijnen als het nieuwe een week zonder terugval draait
en de uitrol-lagen op die dag groen zijn. Tot die tijd is het oude pad geen
rommel maar de weg terug.

#### Scenario: Iemand kijkt op de VM

- **WHEN** iemand na het opruimen op de machine kijkt hoe de chat draait
- **THEN** vindt hij één compose-stack, en geen tweede manier die er ook nog uitziet
  alsof hij werkt

#### Scenario: Het gaat mis in de eerste week

- **WHEN** de compose-kant binnen die week teruggedraaid moet worden
- **THEN** staan de unit, de checkout én het oude volume er nog
