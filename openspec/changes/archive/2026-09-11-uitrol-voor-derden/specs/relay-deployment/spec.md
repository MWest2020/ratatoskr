## REMOVED Requirements

### Requirement: Uitsluitend bereikbaar via het tailnet

**Reason**: dat is een invariant die alleen in één huis klopt, en hij klopte er
zelf ook niet meer (de relay-poort staat op `0.0.0.0`). Sinds
`inloggen-per-persoon` hoort elke aanroep bij een persoon, dus de netwerklaag is
niet langer de enige control. Vervangen door *De standaard is niet bereikbaar,
blootstelling is een keuze*.

## ADDED Requirements

### Requirement: De standaard is niet bereikbaar, blootstelling is een keuze

Een verse installatie SHALL niets buiten de machine publiceren: elke
gepubliceerde poort SHALL een expliciet bind-adres hebben, met loopback als
standaard. Een beheerder die het verder open wil zetten SHALL dat expliciet
doen, en de documentatie SHALL de vormen benoemen die wij ondersteunen —
reverse proxy met TLS, een VPN of tailnet, of bewust het lokale netwerk — met
wat je bij de laatste opgeeft.

De installatie SHALL geen TLS termineren; dat is werk voor de proxy die de
beheerder al heeft. De app SHALL wel correct werken achter zo'n proxy: de rem
op inlogpogingen leest `X-Forwarded-For`, en het sessiecookie krijgt `Secure`
zodra de verbinding niet lokaal is.

#### Scenario: Verse installatie is van buiten niets

- **WHEN** een installatie is opgezet zonder dat de beheerder iets aan
  blootstelling wijzigt
- **THEN** is er vanaf een andere machine geen enkele poort te bereiken

#### Scenario: Blootstellen is één regel, geen verbouwing

- **WHEN** de beheerder de installatie achter zijn reverse proxy wil hangen
- **THEN** volstaat het aanpassen van de bind-adressen in zijn env-bestand
- **AND** hoeft hij niets in de stack zelf te wijzigen

### Requirement: De app wordt uitgerold als gepind image, niet als kopie

De chat SHALL draaien uit een image dat uit deze repo gebouwd is, met een
concrete versietag — nooit `latest`, net als de relay. De installatie SHALL
bestaan uit een compose-bestand en een env-bestand, en SHALL geen bestanden
kennen die met de hand op de machine gezet moeten worden.

Een installatie SHALL kunnen zeggen welke versie er draait.

#### Scenario: Installeren zonder voorkennis

- **GIVEN** een schone machine met docker
- **WHEN** iemand het compose-bestand en een ingevuld env-bestand neerzet en de
  stack start
- **THEN** draait er een boomhuis, en is de enige resterende stap het aanmaken
  van de eigenaar

#### Scenario: Een upgrade is een diff

- **WHEN** een installatie naar een nieuwe versie gaat
- **THEN** is dat één gewijzigde tag in het env- of compose-bestand

### Requirement: Staat overleeft een herinstallatie

Accounts, sessies en push-registraties SHALL in een volume staan dat losstaat
van de container, zodat opnieuw uitrollen of upgraden geen accounts kost.

#### Scenario: Container weg, accounts blijven

- **WHEN** de chat-container verwijderd en opnieuw gestart wordt
- **THEN** bestaan de accounts nog en blijven bestaande sessies geldig
