# chat-native-agents

## REMOVED Requirements

### Requirement: Een agent stuurt de woorden van de mens door, nooit zijn eigen

**Reden:** de eis dwong af dat de doorgestuurde tekst wóórdelijk in het bericht
van de mens stond. Dat bleek verkeerd gericht: het gebruik is niet "papegaai de
mens na" maar "geef deze bevinding door, met duiding". Op 2026-09-14 schreef
odin voor @bouwer een analyse van vier securitybevindingen — precies wat je wilt
doorsturen — en deze eis had het geweigerd.

De vervanger hieronder is bovendien strénger: de listener haalt de inhoud zelf
op, dus een verzonnen citaat is onmogelijk in plaats van alleen verboden.

## ADDED Requirements

### Requirement: Een agent stuurt een bestaand bericht door, met eventueel eigen duiding

Een chat-native agent SHALL een bestaand bericht uit het huidige kanaal kunnen
doorsturen naar een ander kanaal via een `!forward #<kanaal> <bericht-id>`-marker
in zijn antwoord. De listener SHALL de inhoud zelf uit het kanaal ophalen; de
agent SHALL die inhoud niet aanleveren, zodat een verzonnen citaat onmogelijk is
in plaats van alleen verboden.

Een agent MAY een eigen notitie meesturen. Die SHALL onder het citaat staan en
SHALL de naam van de doorstuurder dragen, zodat een lezer haar niet voor het
origineel aanziet.

De listener SHALL aan elk doorgestuurd bericht een bronvermelding toevoegen met
de oorspronkelijke schrijver, het bronkanaal en het bericht-id, en die vermelding
SHALL niet door de agent te schrijven, te wijzigen of weg te laten zijn.

De doelkanalen SHALL uit de handbook-definitie komen (`agent.chat.routes`); een
ontbrekend, leeg of niet-lijstvormig veld SHALL betekenen dat de agent niets mag
doorsturen. Wijst de agent niet eenduidig één bestaand bericht aan, dan SHALL er
niets doorgestuurd worden en SHALL de weigering met reden in #escalatie
verschijnen.

#### Scenario: Een bericht doorgeven met duiding

- **GIVEN** een bericht van mark in #architectuur met id `aaaa1111…`
- **WHEN** odin antwoordt met `!forward #bouw aaaa1111` gevolgd door een eigen notitie
- **THEN** verschijnt in #bouw de inhoud van dát bericht in een blockquote, met
  een bronvermelding die mark, #architectuur en het id noemt, en daaronder de
  notitie onder odins naam

#### Scenario: Een verzonnen id stuurt niets

- **WHEN** odin een bericht-id noemt dat niet in dit kanaal bestaat, of een
  voorvoegsel dat op meerdere berichten past
- **THEN** wordt er niets geplaatst en verschijnt de weigering met reden in
  #escalatie en in het bronkanaal

#### Scenario: Een kanaal buiten het mandaat

- **GIVEN** een agent met `routes: [bouw]`
- **WHEN** hij naar #general wil doorsturen
- **THEN** gaat er niets weg en noemt de weigering welke kanalen wél mogen

### Requirement: Een agent weet wat hij kan, uit zijn eigen definitie

De listener SHALL een agent in zijn systeemprompt vertellen welke mogelijkheden
hij heeft, gegenereerd uit zijn eigen definitie en niet uit losse prompttekst.
Een mogelijkheid die alleen elders in de handbook-definitie beschreven staat
SHALL niet als bekend gelden: `fetch_def` leest de systeemprompt uitsluitend uit
het blockquote onder `## Chat-facet`.

Waar een mogelijkheid gegevens uit het gesprek nodig heeft — zoals een bericht-id
om naar te wijzen — SHALL de prompt die gegevens dragen, en SHALL dat achterwege
blijven bij een agent die de mogelijkheid niet heeft.

#### Scenario: Geen rechten, geen aankondiging

- **GIVEN** een agent zonder `routes` in zijn definitie
- **WHEN** de listener zijn systeemprompt opbouwt
- **THEN** staat er geen doorstuur-instructie in, en dragen de berichten in de
  prompt geen id

#### Scenario: Wel rechten, dus ook het gereedschap om te wijzen

- **GIVEN** een agent met `routes: [bouw]`
- **THEN** noemt zijn systeemprompt `!forward` en alleen #bouw, en dragen de
  berichten in de prompt hun korte id
