## REMOVED Requirements

### Requirement: Schrijven vereist een apparaat-token wanneer de deployment er een zet

**Reason**: één gedeeld token is geen persoon, is niet per persoon in te
trekken en staat op elk apparaat dat het ooit kreeg. Vervangen door sessies uit
de `auth`-capability, die ook lezen afdekken.

### Requirement: De PWA vraagt het token één keer per apparaat

**Reason**: er is geen apparaat-token meer om te vragen. Vervangen door
*De app stuurt je naar inloggen wanneer de sessie ontbreekt*.

## ADDED Requirements

### Requirement: De app stuurt je naar inloggen wanneer de sessie ontbreekt

Krijgt de app een 401, dan SHALL hij naar de inlogpagina gaan en na een
geslaagde login terugkeren naar waar de gebruiker was — hetzelfde kanaal, niet
de voorpagina.

Een 401 SHALL onderscheiden worden van een netwerkfout: het eerste betekent
"jij mag hier niet (meer)", het tweede "ik kan er niet bij". Ze verdienen een
ander antwoord op het scherm.

#### Scenario: Verlopen sessie tijdens gebruik

- **GIVEN** een geopende app waarvan de sessie is verlopen
- **WHEN** de app zijn berichten ophaalt
- **THEN** gaat hij naar de inlogpagina
- **AND** staat de gebruiker na het inloggen weer in hetzelfde kanaal

#### Scenario: Netwerkfout is geen uitlog

- **WHEN** de app zijn berichten niet kan ophalen omdat er geen verbinding is
- **THEN** blijft hij ingelogd en toont hij de verbindingsmelding, niet de
  inlogpagina

### Requirement: Een 401 wist de lokaal bewaarde berichten

Blijkt de sessie ongeldig, dan SHALL de app zijn lokale momentopnamen wissen.
Zonder dat leest de volgende persoon op hetzelfde apparaat de berichten van de
vorige — de momentopname is er voor "geen verbinding", niet voor "geen
toegang".

Een netwerkfout SHALL de momentopnamen juist laten staan.

#### Scenario: Uitgelogd op een gedeeld apparaat

- **GIVEN** een apparaat met bewaarde berichten van een vorige gebruiker
- **WHEN** de app een 401 krijgt
- **THEN** zijn die berichten weg voordat de inlogpagina verschijnt
