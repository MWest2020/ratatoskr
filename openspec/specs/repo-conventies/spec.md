# repo-conventies Specification

## Purpose

De regels over hoe deze repo eruitziet, en het bewijs dat ze ook echt gelden.

Eén regel met tanden is meer waard dan tien in een CONTRIBUTING.md, dus staat
hier alleen wat een script kan controleren: bestanden blijven binnen 200 regels,
en een baseline voor wat al te lang was mag alleen korter worden. Dat tweede is
de belangrijkste helft — een baseline zonder vervaldatum is een uitzondering die
zichzelf vermenigvuldigt.

## Requirements

### Requirement: Bronbestanden blijven binnen 200 regels, gecontroleerd in CI

Elk bronbestand dat we zelf schrijven — `*.py`, `*.js`, `*.sh`, `*.css`,
`*.html` en `Dockerfile`, tests inbegrepen — SHALL hoogstens 200 regels hebben.
Markdown, `LICENSE`, binaire bestanden, YAML/JSON-data en vendored configuratie
SHALL buiten die grens vallen, met de reden per categorie in de check zelf. De
check SHALL op elke PR en elke push naar `main` in CI draaien, samen met de
unittests uit `verify.sh`, en SHALL lokaal met dezelfde opdracht te draaien zijn.

#### Scenario: Een bestand groeit over de grens

- **WHEN** een PR een bronbestand boven de 200 regels brengt
- **THEN** is de check rood en noemt hij het bestand en het aantal regels

#### Scenario: Buiten de scope telt niet

- **WHEN** een spec, een design of het vendored compose-bestand boven de 200
  regels komt
- **THEN** blijft de check groen

#### Scenario: Lokaal hetzelfde oordeel

- **WHEN** iemand `bash verify.sh` draait op dezelfde commit als CI
- **THEN** geeft de check hetzelfde oordeel

### Requirement: Een baseline is tijdelijk

Een bestand dat bij het aanzetten van de check al boven de grens zat, MAG op een
baseline staan met zijn aantal regels van dat moment. Zo'n bestand SHALL niet
groeien, en SHALL van de baseline af zodra het binnen de grens valt. Een
baseline SHALL alleen bestaan zolang de change die hem invoerde niet
gearchiveerd is.

#### Scenario: Baseline-bestand groeit

- **WHEN** een PR een regel toevoegt aan een bestand op de baseline
- **THEN** is de check rood

#### Scenario: Gesplitst maar niet afgevoerd

- **WHEN** een bestand op de baseline onder de 201 regels komt en nog op de
  baseline staat
- **THEN** is de check rood tot het van de baseline af is, zodat de baseline
  niet stil blijft staan
