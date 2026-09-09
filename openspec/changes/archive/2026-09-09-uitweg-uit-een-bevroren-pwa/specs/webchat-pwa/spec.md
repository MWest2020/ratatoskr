## ADDED Requirements

### Requirement: De app is uit een vastgelopen staat te krijgen zonder herinstallatie

De webchat SHALL de gebruiker een handeling bieden die elke service
worker afmeldt, elke cache wist en de app opnieuw laadt. Die handeling
SHALL bereikbaar zijn juist wanneer de app zijn gegevens niet kan laden —
dat is het moment waarop hij nodig is.

De app SHALL zichzelf niet ongevraagd wissen: een storing van enkele
seconden mag geen lokale staat kosten. Het is een knop, geen automatisme.

De service worker SHALL geregistreerd worden zodat zijn script niet uit
de HTTP-cache komt, zodat een nieuwe versie bij de eerstvolgende start
wordt opgemerkt.

#### Scenario: Vastgelopen app komt los

- **GIVEN** een geïnstalleerde app die op een oude, gecachete versie
  hangt
- **WHEN** de gebruiker *app verversen* kiest
- **THEN** worden service workers afgemeld en caches gewist, en laadt de
  app opnieuw als de versie die de server nu serveert

### Requirement: Een verbindingsfout noemt het adres en de oorzaak

Wanneer de app zijn gegevens niet kan laden SHALL hij tonen welk adres
hij probeerde en welke fout terugkwam. Een melding die alleen "geen
verbinding" zegt, maakt geen verschil zichtbaar tussen een tunnel die nog
niet op is en een app die naar een adres wijst dat niet meer bestaat.

#### Scenario: De melding is bruikbaar

- **WHEN** de app zijn gegevens niet kan laden
- **THEN** noemt de melding het adres waar hij het probeerde
- **AND** de fout die daarbij terugkwam
