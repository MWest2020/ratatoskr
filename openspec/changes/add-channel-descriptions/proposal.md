## Why

De kanaallijst toont alleen namen — je ziet niet waar een kanaal voor is of of het
werkt (Mark: "#runs is leeg, dus of het werkt niet of het moet weg"). De relay
ondersteunt native kanaal-beschrijvingen; die staan nu niet in de app.

## What Changes

- **Native kanaal-beschrijvingen** gezet vanuit `channels.yml`'s `doel` (via
  `buzz channels update --description`); `channels list` geeft ze mee.
- **App toont de beschrijving** per kanaal in de lade (subtitel onder de naam),
  zodat je per kanaal ziet waar het voor is.
- **`ping.sh` krijgt een `CHAN`-param** (default `general`) zodat uitkomsten naar
  #review/#runs kunnen i.p.v. alleen #general — de basis om review-verdicts naar
  #review en build-runs naar #runs te posten (dan vult #runs zich).
