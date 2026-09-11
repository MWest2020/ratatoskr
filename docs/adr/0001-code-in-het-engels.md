---
status: aanvaard
datum: 2026-09-11
beslisser: Mark
---

# ADR-0001 — Code in het Engels, proza in het Nederlands

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

Nederlands: documentatie, `design.md`/`proposal.md`, README's, commit-teksten,
PR-beschrijvingen, chatberichten, en de **commentaren in de code**.

Die laatste is bewust. Het commentaar in deze repo legt uit *waarom* iets zo is
— welke storing eronder zat, welk alternatief is verworpen, welke meting het
besluit droeg. Dat is proza, het is het waardevolste wat er staat, en Mark
schrijft en leest het in het Nederlands. Een codebase met Engelse namen en
Nederlandse uitleg is normaal in Nederland; het omgekeerde is dat niet.

Strings die een **gebruiker** ziet (foutmeldingen in de chat, teksten in de PWA,
de uitvoer van `adminctl`) blijven Nederlands: dat is interface, geen code.

## Gevolgen

- **Nieuwe en gewijzigde code volgt de regel meteen.**
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

- **Alles Engels, ook commentaar en docs.** Consistent, en het is wat de meeste
  open source doet. Verworpen: het commentaar is hier uitleg voor Mark, geschreven
  op het moment dat de meting vers is. Dat in een tweede taal opschrijven maakt
  het korter en armer, en armoede in de uitleg is precies wat deze repo niet
  wil.
- **Alles Nederlands, zoals het gegroeid was.** Intern verdedigbaar zolang één
  persoon het leest. Onhoudbaar zodra er een derde installeert of meebouwt, en
  dat is expliciet de richting.
- **Geen regel, per bestand kiezen.** Dat is wat we tot vandaag hadden, en het
  levert een codebase waarin je per bestand moet raden.
- **Bestaande code gaandeweg omzetten.** Klinkt zachter, maar levert jaren van
  halfslachtigheid op. Eén mechanische change, of niet.
