## ADDED Requirements

### Requirement: Kanaalbeheer tekent als agent, nooit als de mens

Kanalen maken, verwijderen en leden toevoegen SHALL ondertekend worden met de
orchestrator-identiteit. De mens-sleutel SHALL nergens in de lopende dienst voor
kanaalbeheer gebruikt worden; is er geen orchestrator-sleutel geconfigureerd, dan
SHALL de actie geweigerd worden met een leesbare melding in plaats van terug te
vallen op een andere identiteit.

#### Scenario: Nieuw kanaal is agent-owned

- **WHEN** een gebruiker in de web-chat een kanaal aanmaakt
- **THEN** is de orchestrator de eigenaar van dat kanaal, en kan geautomatiseerd
  kanaalbeheer het daarna zonder mens-sleutel bijwerken

#### Scenario: Geen orchestrator-sleutel geconfigureerd

- **WHEN** kanaalbeheer wordt aangeroepen terwijl er geen orchestrator-sleutel in
  de serveromgeving staat
- **THEN** faalt de actie zichtbaar met de melding dat kanaalbeheer uit staat, en
  wordt er niets met een andere identiteit ondertekend

### Requirement: Bestaande mens-owned kanalen zijn overdraagbaar

Er SHALL een herhaalbaar, idempotent script bestaan dat het eigenaarschap van
mens-owned kanalen overdraagt aan de orchestrator zonder het kanaal opnieuw aan
te maken, met behoud van id, leden en geschiedenis.

#### Scenario: Overdracht van een mens-owned kanaal

- **WHEN** het overdrachtsscript draait op een kanaal waarvan de mens eigenaar is
- **THEN** is de orchestrator daarna eigenaar, geverifieerd tegen de relay, en
  laat een tweede run het kanaal ongemoeid
