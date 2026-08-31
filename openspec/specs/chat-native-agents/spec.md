# chat-native-agents Specification

## Purpose
TBD - created by archiving change add-chat-native-agents. Update Purpose after archive.
## Requirements
### Requirement: Tweede agentklasse met eigen kooi-principes

Chat-native agents SHALL langlopend draaien via `buzz-acp` met een eigen
keypair uit de registry, op een eigen host buiten de habitat-namespace, zonder
git-push-credentials; hun deliverable is tekst in kanalen.

#### Scenario: Uitkomst wil code worden

- **WHEN** een gesprek uitmondt in een gewenste codewijziging
- **THEN** ontstaat die via een OpenSpec-change en een habitat-run, nooit
  doordat de chat-agent zelf ergens pusht

### Requirement: Mandaat buiten bereik van de agent

Het mandaat van elke chat-native agent SHALL in de boomhuis-repo leven en voor de
agent zelf niet wijzigbaar zijn; een agent die zijn mandaat, sleutels of
relay-configuratie kan aanpassen is een harde fout.

#### Scenario: Poging tot zelfverbouwing

- **WHEN** een agent probeert zijn mandaat of configuratie te wijzigen
- **THEN** faalt dat aantoonbaar en wordt het als incident geëscaleerd

### Requirement: Begrensd bestaan

Elke chat-native agent SHALL een idle-timeout (automatische reaping) en een
budgetplafond hebben; overschrijding SHALL de agent stoppen en escaleren, niet
stilzwijgend doorbranden.

#### Scenario: Nachtrust

- **WHEN** een agent de idle-timeout bereikt
- **THEN** draint hij lopende beurten, publiceert offline-presence en stopt

### Requirement: Zelfde audit-lat als de kooi

Elk agent-bericht SHALL via de Nostr-signatuur herleidbaar zijn tot de
rol-identiteit, en het relay-log SHALL doorzoekbaar zijn; anonieme of geleende
identiteiten bestaan niet.

#### Scenario: Wie zei dit

- **WHEN** later de vraag rijst welke agent een uitspraak deed
- **THEN** geeft de signatuur + registry daar eenduidig antwoord op

