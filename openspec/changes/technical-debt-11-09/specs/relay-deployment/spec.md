# relay-deployment

## MODIFIED Requirements

### Requirement: Gepind image

Elk image waaruit een installatie draait — de relay, de chat en de ondersteunende
services — SHALL letterlijk gepind staan in het gecommitte compose-bestand: een
commit-SHA, een digest, of een versietag met minstens major en minor. Nooit
`:main`, `:latest`, alleen een major, of een variabele met of zonder fallback;
een image-pin SHALL niet in een env-bestand staan. Een upgrade is een bewuste
pin-wijziging in git. Het chat-image SHALL de buzz-CLI bouwen uit dezelfde
upstream-commit als het relay-image. Een check in CI SHALL dit controleren, en
SHALL ook eisen dat workflows die images bouwen hun actions per commit-SHA pinnen.

#### Scenario: Upgrade is een diff

- **WHEN** de relay of de chat naar een nieuwe versie gaat
- **THEN** is dat zichtbaar als één gecommitte pin-wijziging in het
  compose-bestand, herleidbaar tot wie/wanneer/waarom

#### Scenario: Een drijvende pin komt niet door

- **WHEN** een PR een `image:` introduceert zonder concrete versie, met `:main`
  of `:latest`, met alleen een major, of als `${VAR}` of `${VAR:-…}`
- **THEN** is de check rood en noemt hij bestand en regel

#### Scenario: Relay en buzz-CLI lopen uiteen

- **WHEN** de relay-tag verandert en `BUZZ_REF` in `chat/Dockerfile` niet mee
- **THEN** is de check rood

## ADDED Requirements

### Requirement: Eén uitrolpad, ook voor de eigen installatie

Er SHALL één uitrolpad zijn: het compose-bestand en het chat-image uit deze
repo. De installatie van de beheerder zelf SHALL daarop draaien; een tweede,
handmatige weg — bestanden kopiëren, een losse systemd-unit, een compose-kopie
in een andere repo — SHALL niet bestaan. De eigen installatie SHALL over dat pad
gemigreerd zijn voordat een installatie bij een derde live gaat.

#### Scenario: Marks chat komt uit hetzelfde image

- **WHEN** de chat op Marks relay-VM draait
- **THEN** draait hij uit het gepinde image en het compose-bestand uit deze repo
- **AND** draait er geen `boomhuis-chat.service` en geen code uit
  `/opt/buzz-build`

#### Scenario: De migratie kost niets

- **WHEN** Marks installatie van systemd naar de compose-stack gaat
- **THEN** bestaan accounts, sessies en push-registraties daarna nog
- **AND** heeft de relay dezelfde identiteit, kanalen en berichten

#### Scenario: Geen derde vóór Mark

- **WHEN** een installatie bij een derde live zou gaan terwijl Marks chat nog
  via `scp` en systemd draait
- **THEN** gaat die installatie niet live
