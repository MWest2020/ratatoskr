## Why

De spec loopt achter op de code. `channel-topology` beschrijft nog dat een nieuw
kanaal **"de coordinator"** als lid krijgt en dat de respons dat meldt via
`coordinator_added`. De code doet sinds boomhuis#41 iets anders: hij zoekt de hub
op **rol** (`meta-agent`) en antwoordt met `hub_added`.

Dat verschil is niet cosmetisch. Precies die naam-koppeling brak: na de
hernoeming `coordinator` → `odin` gaf elk nieuw kanaal `coordinator_added: false`
met "geen cid/pubkey", en er kwam dus in geen enkel nieuw kanaal nog een hub te
zitten — stil, want de add is best-effort. Een spec die de naam noemt, nodigt die
fout opnieuw uit.

## What Changes

- De requirement spreekt van **de hub-agent, gevonden op rol**, niet van een
  agent bij naam. Het antwoordveld heet `hub_added`.
- Dezelfde correctie in `chat-native-agents`, waar "de coordinator-default" als
  voorbeeld van een lidmaatschapsbron stond.

Geen codewijziging: dit brengt de spec op de code, niet andersom.
