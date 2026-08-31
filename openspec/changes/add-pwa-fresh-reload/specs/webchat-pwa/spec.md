## ADDED Requirements

### Requirement: Verse herlaad toont de laatste versie

De geïnstalleerde PWA SHALL bij een herlaad online de nieuwste gedeployde versie
tonen, niet een oudere gecachete versie; de service worker is netwerk-eerst voor
de pagina, met de cache als fallback wanneer het netwerk niet of niet op tijd
(binnen een korte timeout) reageert.

#### Scenario: Herlaad toont de laatste versie

- **WHEN** de gebruiker de geïnstalleerde app herlaadt terwijl hij online is en
  het netwerk op tijd antwoordt
- **THEN** toont de app de nieuwste gedeployde versie, niet een oudere cache

#### Scenario: Traag of geen netwerk valt terug op de cache

- **WHEN** de gebruiker de app opent terwijl het netwerk onbereikbaar is of niet
  binnen de timeout antwoordt (bv. een koude launch vóór de tailnet-tunnel op is)
- **THEN** toont de app snel de laatst gecachete versie in plaats van te hangen of
  te falen, en ververst de cache alsnog zodra het netwerk antwoordt
