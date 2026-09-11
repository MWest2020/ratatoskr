# Change: dagelijkse zettelkast-terugkoppeling

## Why

Mark deelt clips vanaf zijn telefoon; die landen in `sources/` van de zettelkast.
Wat er daarna mee gebeurt, gebeurde tot vandaag alleen als iemand het startte.
Gemeten 2026-09-11: 21 bronnen ongecaptured, waarvan zeven binnengekomen na
5 september — de `zettelkast-daily`-timer stond op deze host simpelweg niet
geïnstalleerd. Dat is nu rechtgezet (dat is huishouding, geen change).

Wat de change wél nodig heeft: **Mark ziet het resultaat niet.** De capture
draait in de zettelkast en schrijft daar in `wiki/log.md`; boomhuis meldt er
niets over. De bestaande job `news_from_zettelkast` is weekelijks en gaat over
inhoud ("wat is er interessant"), niet over verwerking ("wat is er gedaan, en wat
blijft liggen"). Mark, 2026-09-11: *"dat moet dagelijks gecaptured worden,
geanalyseerd en het resultaat naar boomhuis."*

## What Changes

- Een **dagelijkse job** `zettelkast_dagelijks` die na de capture-run kijkt wat
  er die dag verwerkt is, wat er nog openstaat, en wat daarmee zou moeten
  gebeuren — en dat in `#news_from_zettelkast` post.
- De context maakt het onderscheid dat `scripts/new_sources.py` niet maakt:
  een clip waarvan de **fetch-snapshot** al gecaptured is, is afgehandeld, ook al
  citeert geen enkele wiki-pagina het clipbestand zelf. Zonder dat onderscheid
  meldt de job elke dag dezelfde twaalf "achterstanden" die er geen zijn.
- Best-effort, zoals elke recurring job: een leeg of gefaald antwoord post niets
  en laat niets falen. Een LEESFOUT in de context wordt expliciet gemeld, zodat
  een storing nooit als "niets te doen" leest.

## Impact

- Gewijzigd: `jobs/jobs.yml`, `jobs/README.md`, `jobs/systemd/` (nieuwe timer).
- Spec: `recurring-jobs` krijgt er één requirement bij.
- Raakt de zettelkast-repo niet: die weet niets van boomhuis, boomhuis leest.
