## ADDED Requirements

### Requirement: Verse herlaad toont de laatste versie

De geïnstalleerde PWA SHALL bij een herlaad online de nieuwste gedeployde versie
tonen, niet een oudere gecachete versie; de service worker is netwerk-eerst voor
de pagina, met de cache uitsluitend als offline-fallback.

#### Scenario: Herlaad toont de laatste versie

- **WHEN** de gebruiker de geïnstalleerde app herlaadt terwijl hij online is
- **THEN** toont de app de nieuwste gedeployde versie, niet een oudere cache

#### Scenario: Offline valt terug op de cache

- **WHEN** de gebruiker de app opent zonder netwerk
- **THEN** toont de app de laatst gecachete versie in plaats van te falen
