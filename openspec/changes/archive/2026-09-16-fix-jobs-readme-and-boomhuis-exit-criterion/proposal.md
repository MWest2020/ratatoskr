# Change: fix-jobs-readme-and-boomhuis-exit-criterion

## Why

Twee restjes van de hernoeming naar `ratatoskr`, allebei klein, allebei van het
soort dat blijft liggen omdat het nooit dringend is.

`jobs/README.md` legt onder "Nieuwe job toevoegen" uit hoe je een job maakt, en
noemt daar `boomhuis-job@` en `boomhuis-<x>.timer`. Die units heten al maanden
`ratatoskr-*`. Wie de instructie volgt, bouwt iets dat niet werkt — en documentatie
die niet werkt is erger dan geen documentatie, want ze kost eerst tijd voordat ze
faalt.

`chat/settings.py` leest `BOOMHUIS_*` nog als terugval naast `RATATOSKR_*`. Dat
was een goede keuze bij de hernoeming: installaties kunnen erop gepind zijn. Maar
er staat geen einde aan. Een terugval zonder exit-criterium is geen overgang maar
een tweede permanente naam, en over een jaar durft niemand hem meer weg te halen
omdat niemand weet of er nog iets op leunt.

## What Changes

- `jobs/README.md`: de unit-namen kloppend maken.
- `chat/settings.py`: een exit-criterium bij de `BOOMHUIS_`-terugval —
  **zodra geen enkele live `.env` die prefix nog gebruikt, schrapt een eigen
  change de terugval.** Nu alleen vastleggen; niet verwijderen.

## Wat hier NIET in zit

De terugval zelf weghalen. Dat is precies de change die dit criterium later
mogelijk maakt, en hem nu al doen zou de installaties raken die we juist wilden
ontzien.

## Impact

- `jobs/README.md`, `chat/settings.py`. Documentatie en een commentaar; geen
  nieuw schrijfpad, geen secret, geen gedragsverandering.
- Gate: normale review. Geen security-run nodig.
