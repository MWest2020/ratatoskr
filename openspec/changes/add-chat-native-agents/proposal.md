## Why

Habitat kan alleen rollen huisvesten waarvan het deliverable een git-branch is.
Rollen waarvan het deliverable een gesprek of een tekst is — marketing,
architectuur-sparring, straks meer — hebben geen bestaansplek. Buzz' eigen
agent-model (`buzz-acp`: een langlopend proces met een keypair, aangestuurd via
relay-berichten) is daar precies voor gemaakt. Fase 2 introduceert die tweede
agentklasse, met eigen kooi-principes die dezelfde lat halen als habitat.

## What Changes

- **`agents/<rol>/mandaat.md`**: per chat-native agent een mandaat in deze repo
  (read-only voor de agent zelf): doel, toon, wat autonoom mag, wat escaleert,
  wat verboden is. Eerste twee rollen: `marketing` en `architect-sparring`.
- **`agents/<rol>/`**: de `buzz-acp`-configuratie (systemprompt, idle-timeout,
  toegestane agent-backend, budgetplafond) als env-contract, sleutels via de
  registry + SOPS+age.
- **Hosting**: langlopend proces op een eigen host (VM/LXC), uitdrukkelijk níet
  in de habitat-namespace; `buzz-backend-kubernetes` is een latere optie, geen
  startpunt.

## Capabilities

### New Capabilities

- `chat-native-agents`: de tweede agentklasse — langlopend, keypair-identiteit,
  conversatie-deliverables, eigen kooi-principes (geen push-credentials, geen
  mandaat-zelfbeheer, idle-reaping, budgetplafond).

### Modified Capabilities

<!-- Geen: habitat-rollen en hun specs blijven ongewijzigd. -->

## Impact

- Nieuwe langlopende processen = nieuw aanvalsoppervlak; daarom dezelfde
  denkwijze als de kooi: minimale rechten, geen repo-schrijftoegang, alles
  herleidbaar via de relay-signatuur.
- Kosten: langlopend ≠ altijd actief; idle-reaping en een budgetplafond per
  agent zijn onderdeel van de spec, niet een optie.
- Vergt fase 0 en 1 (relay, registry, kanalen) als fundament.
