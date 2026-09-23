## MODIFIED Requirements

### Requirement: Een kanaal mag een standaard-agent noemen

Een kanaal SHALL in `channels.yml` een `default_agent` kunnen noemen. Een
menselijk bericht zonder vermelding en zonder vervolgdoel SHALL dan naar
die agent gaan. Dat is opt-in per kanaal: zonder `default_agent` SHALL een
kanaal zich gedragen zoals voorheen.

De volgorde van de drie triggers is het contract en SHALL vastliggen:
een **vermelding** gaat vóór een **vervolg**, en een vervolg gaat vóór de
**standaard-agent**. Voor het vervolg SHALL alleen de meest recente agent in
de laatste tien berichten tellen; mensen daartussen breken het niet. Mag
die agent hier niet vervolgen — hij antwoordde op een vermelding via
relay-lidmaatschap — dan is er niets te vervolgen en SHALL het bericht
als koude start gelden: de standaard-agent antwoordt. Stilte zou er
precies uitzien als een listener die niet draait. Bij elke beurt SHALL de reden noemen welke regel
afging, zodat een log een lopend gesprek kan onderscheiden van een koude
start.

Alles wat al gold, blijft gelden: een agent SHALL nooit op een andere agent
antwoorden, een markeringsregel (`!sessie`, `!route`) SHALL via zijn eigen
pad lopen, en een agent SHALL alleen spreken waar zijn definitie en het
relay-lidmaatschap dat toestaan.

De listener SHALL weigeren te starten als een kanaal een standaard-agent
noemt die in dat kanaal niet mag spreken — liever niet opstarten dan
stilzwijgend nooit antwoorden.

#### Scenario: Koude start gaat naar de standaard-agent

- **GIVEN** `#general` met `default_agent: odin`
- **WHEN** een mens een bericht zonder vermelding plaatst en er geen agent
  in de laatste tien berichten sprak
- **THEN** odin antwoordt, en de reden in het log noemt de standaardregel

#### Scenario: Een vermelding gaat voor de standaard

- **GIVEN** `#general` met `default_agent: odin`
- **WHEN** een mens `@architect` vermeldt
- **THEN** architect antwoordt, niet odin

#### Scenario: Een lopend gesprek gaat voor de standaard

- **GIVEN** `#general` met `default_agent: odin`, en architect — wiens
  definitie `#general` noemt — sprak drie berichten geleden
- **WHEN** een mens zonder vermelding reageert, ook als er intussen een
  ander mens iets zei
- **THEN** architect antwoordt als vervolg, niet odin

#### Scenario: Een recente agent die hier niet mag vervolgen, geeft de beurt aan de standaard

- **GIVEN** `#general` met `default_agent: odin`, en architect — wiens
  definitie `#general` niet noemt — antwoordde net op een vermelding
- **WHEN** een mens zonder vermelding reageert
- **THEN** antwoordt odin, met reden `default`

#### Scenario: Buiten het venster valt het vervolg weg

- **GIVEN** `#general` met `default_agent: odin`, en architect sprak meer
  dan tien berichten geleden
- **WHEN** een mens zonder vermelding iets zegt
- **THEN** odin antwoordt, want er is geen vervolgdoel meer

#### Scenario: Een kanaal zonder standaard blijft stil bij een koude start

- **GIVEN** `#statistics` zonder `default_agent`
- **WHEN** een mens zonder vermelding iets zegt en er geen vervolgdoel is
- **THEN** antwoordt er niemand

#### Scenario: Een standaard die niet mag spreken, houdt de start tegen

- **GIVEN** `channels.yml` noemt als `default_agent` een agent wiens
  definitie dat kanaal niet toestaat
- **WHEN** de listener opstart
- **THEN** weigert hij te starten en noemt hij kanaal en agent
