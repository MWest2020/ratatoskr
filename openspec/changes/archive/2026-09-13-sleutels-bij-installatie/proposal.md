# Change: sleutels ontstaan bij de installatie, niet in Marks git

## Why

Derde stap richting het product, na `inloggen-per-persoon` (authenticatie) en
`uitrol-voor-derden` (een image in plaats van een gekopieerde map). Wat er nu
nog tussen zit is het onderwerp waar `docs/naar-een-product.md` invariant 3
noemt:

> Identiteiten en sleutels leven in Marks git. `identities.yml` staat in deze
> repo, privésleutels via SOPS+age met Marks sleutel. Een installatie bij een
> ander moet zijn eigen sleutelpaar per identiteit genereren, bij installatie,
> in een sleutelopslag op die installatie — niet in een repo.

Vandaag zegt `identity-registry` letterlijk dat privésleutels "uitsluitend
SOPS+age-versleuteld in `secrets/`" staan, en `agents/run.sh` doet precies dat:
`sops -d secrets/identities.yaml` met Marks age-sleutel. Een derde die dit
installeert heeft geen van beide en kan geen agent starten.

Er zit ook een stille aanname in die pas pijn doet bij iemand anders: elke
installatie die deze repo gebruikt zou dezelfde agent-sleutels hebben. Twee
installaties, dezelfde npub, één relay die ze niet uit elkaar kan houden. Dat is
geen theoretisch bezwaar — het is de reden dat "één installatie = één team"
(besluit C) op sleutelniveau niet waar is zolang de sleutels uit de repo komen.

## What Changes

- **Een sleutelopslag als naad.** Waar een privésleutel vandaan komt wordt een
  keuze van de installatie in plaats van een eigenschap van de repo. Twee
  backends: `sops` (wat Marks installatie nu doet — die moet blijven werken) en
  `bestand`, een map op de installatie met mode 0600 per sleutel.
- **Genereren bij installatie.** Een verse installatie maakt zijn eigen
  sleutelpaar per identiteit, met de code die `deploy/sleutelpaar.sh` al heeft,
  en schrijft de publieke helft in de lokale `identities.yml`. De privéhelft
  komt in de opslag en verschijnt nergens anders.
- **`identities.yml` blijft de publieke registry**, maar hoort bij de
  *installatie*, niet bij de repo. Wat in git staat is het voorbeeld waarmee
  Marks installatie draait; een verse installatie schrijft zijn eigen.
- **Fail-closed blijft fail-closed.** Ontbreekt een privésleutel, dan start die
  agent niet en staat de reden op stdout — zoals nu. Wat verandert is alleen
  waar hij gezocht wordt.

## Wat dit NIET is

Geen sleutelrotatie, geen HSM, geen OpenBao. Die horen in het rijtje maar niet
in deze change: dit gaat over het ene ding dat een derde tegenhoudt, en dat is
dat er überhaupt sleutels ontstaan die van hem zijn.

En geen migratie van Marks installatie. Die blijft op de `sops`-backend staan;
dat is de terugweg, en een terugweg gooi je niet weg in de change die de nieuwe
weg aanlegt.

## Impact

- Nieuw: `agents/keystore.py` + tests.
- Nieuw: `scripts/init_identities.py` — genereert ontbrekende sleutelparen.
- Gewijzigd: `agents/run.sh` (backend-keuze), `agents/bootstrap.py` (npub uit de
  lokale registry), spec `identity-registry`.
- `deploy/sleutelpaar.sh` blijft, maar de logica komt ook in Python te staan
  zodat de installatie geen docker nodig heeft om één sleutel te maken.
