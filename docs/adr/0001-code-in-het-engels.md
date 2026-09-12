---
status: aanvaard
datum: 2026-09-11
beslisser: Mark
---

# ADR-0001 — Engels in de repo, Nederlands in het gesprek

## Context

`CLAUDE.md` zei tot vandaag alleen: *"Nederlands in proza; technisch jargon en
citaten blijven Engels."* Dat is over code nooit een uitspraak geweest, en in de
praktijk is het die kant op gegroeid: `instellingen.lees()`, `sessiepoort.py`,
`mag_starten()`, `knip_marker()`, `bouwen.sh`, `na-uitrol.sh`. Consequent
Nederlands, en precies daarom viel het pas op toen het al overal zat.

Mark, 2026-09-11: *"moet wel in adr dat we code in engels willen. wtf. ik heb
bijna nooit code in nederlands gezien."*

Dat laatste is het echte argument. Nederlandse identifiers zijn niet fout, ze
zijn *ongebruikelijk* — en dat kost op drie plekken:

- **Vreemde ogen.** Ratatoskr gaat naar derden. Een ontwikkelaar die hier voor
  het eerst binnenkomt leest `mag_starten(cfg, typ, starter, aanleiding)` en moet
  eerst een taal leren voordat hij de logica ziet.
- **De omgeving is Engels.** `subprocess`, `Popen`, `flock`, `assetlinks`,
  `versionName`. Nederlandse namen ertussen geven een permanente codewissel:
  `for s in self.lopend: s["proc"].poll()`.
- **Gereedschap.** Modellen, linters, zoekacties en voorbeelden zijn op Engelse
  identifiers getraind. Nederlandse namen maken alles net iets minder scherp.

## Besluit

**Code is Engels. Proza is Nederlands.**

Engels: bestandsnamen, modulenamen, functie- en variabelenamen, klassen,
constanten, CLI-subcommando's, veldnamen in YAML/JSON die code leest, en
testnamen.

**Tweede herziening (2026-09-12).** De eerste versie hield documentatie,
commit-teksten en commentaar in het Nederlands, met als redenering dat Mark ze
in het Nederlands schrijft en leest. Dat bleek de verkeerde afleiding. Mark:
*"default is engels. ik praat alleen nederlands met jou."*

Dus: **Engels is de standaard voor alles wat in de repo geschreven staat** —
code, commentaar, documentatie, `design.md`, README's, commit-teksten,
PR-beschrijvingen. Nederlands is de taal van het *gesprek*, niet van de
artefacten. Dat onderscheid is het hele punt: wat blijft staan wordt door
anderen gelezen, wat we tegen elkaar zeggen niet.

Strings die een **gebruiker** ziet zijn **standaard Engels**, met Nederlands als
optie. Dat is een herziening: de eerste versie van deze ADR zette de interface op
Nederlands omdat het toen één gebruiker bediende. Mark, 2026-09-11: *"interface
moet toch ook engels ondersteunen. niet over nagedacht eerder, maar eigenlijk
default engels."* Ratatoskr gaat naar derden, en een installatie die je alleen in
het Nederlands kunt bedienen is daar onbruikbaar.

Gevolg: **nieuwe interfaceteksten zijn meteen Engels.** De bestaande Nederlandse
teksten gaan in één aparte change over naar een taallaag met `en` als default en
`nl` ernaast — zelfde redenering als bij de identifiers: half omgezet is
slechter dan niet omgezet.

## Gevolgen

- **Nieuwe en gewijzigde code volgt de regel meteen.**
- **Nieuwe repo's beginnen meteen in het Engels.** Draupnir (twee dagen oud) is
  op 2026-09-12 volledig omgezet; dat kostte een half uur en over een maand had
  het een dag gekost.
- **Bestaande code wordt in één aparte, mechanische change omgezet**, niet
  gaandeweg. Half omgezet is slechter dan niet omgezet: dan moet je bij elke
  naam raden in welke taal hij staat. Die change raakt `chat/`, `agents/`,
  `jobs/` en `orchestrator/`, en leunt op de bestaande 116+ unittests om te
  bewijzen dat er alleen namen veranderden.
- **Publieke contracten veranderen apart, of niet.** De marker `!sessie`, de
  instellingnamen `RATATOSKR_*`, de route `/ratatoskr.apk` en de
  kanaalnamen zijn afspraken met mensen en met draaiende installaties. Die
  hernoemen is een aparte afweging per geval, geen bijwerking van deze ADR.
- `CLAUDE.md` verwijst naar deze ADR in plaats van het in één regel af te doen.

## Verworpen alternatieven

- **Commentaar en docs in het Nederlands** (de eerste versie van deze ADR).
  Verworpen na een dag: het argument was "Mark leest het in het Nederlands",
  maar Mark leest Engels net zo goed en de artefacten zijn voor iedereen ná ons.
  De vrees dat uitleg in een tweede taal armer wordt, blijft staan als
  aandachtspunt — niet als reden om het niet te doen.
- **Alles Nederlands, zoals het gegroeid was.** Intern verdedigbaar zolang één
  persoon het leest. Onhoudbaar zodra er een derde installeert of meebouwt, en
  dat is expliciet de richting.
- **Interface alleen Nederlands** (de eerste versie van deze ADR). Herzien: zie
  hierboven. Eén taal in de interface is een keuze die je maakt vóór je klanten
  hebt, en dan nooit meer goedkoop kunt terugdraaien.
- **Geen regel, per bestand kiezen.** Dat is wat we tot vandaag hadden, en het
  levert een codebase waarin je per bestand moet raden.
- **Bestaande code gaandeweg omzetten.** Klinkt zachter, maar levert jaren van
  halfslachtigheid op. Eén mechanische change, of niet.
