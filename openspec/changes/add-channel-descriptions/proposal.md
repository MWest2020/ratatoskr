## Why

De kanaallijst toont alleen namen — je ziet niet waar een kanaal voor is of of het
werkt (Mark: "#runs is leeg, dus of het werkt niet of het moet weg"). De relay
ondersteunt native kanaal-beschrijvingen; die staan nu niet in de app.

## What Changes

- **Native kanaal-beschrijvingen** gezet vanuit `channels.yml`'s `doel` (via
  `buzz channels update --description`); `channels list` geeft ze mee.
- **App toont de beschrijving** per kanaal in de lade (subtitel onder de naam),
  zodat je per kanaal ziet waar het voor is.
- **`ping.sh` krijgt een `CHAN`-param** (default `general`) zodat een bericht naar
  een gekozen kanaal kan i.p.v. alleen #general. Review-verdicts gaan hiermee naar
  #review (via de reviewer-identiteit). Build-run-uitkomsten naar #runs is een
  vervolgstap: de CHAN-param maakt het mogelijk, maar het automatisch posten bij
  elke dispatch wordt apart aangesloten — #runs vult zich dus nog niet vanzelf.

Beschrijvingen worden gezet met de **orchestrator-sleutel** (een agent), niet met
marks mens-sleutel. Kanalen die nu nog door de mens (chat-backend) zijn aangemaakt
kan de orchestrator niet updaten; die worden gemeld → aparte follow-up
`reown-channels-to-orchestrator`.
