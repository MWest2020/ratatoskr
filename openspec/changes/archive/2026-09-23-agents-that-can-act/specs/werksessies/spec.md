## ADDED Requirements

### Requirement: Research-type om iets op het open web op te zoeken

Er SHALL een sessietype `research` bestaan waarmee de hub iets laat opzoeken
zonder het zelf te doen. Het type SHALL geen repository lezen en niets
schrijven: geen werkmap in een repo, maar een eigen kladmap, en als
gereedschap alleen `Read`, `Grep`, `Glob` en `WebFetch`. Starten mogen Mark,
de orchestrator en odin; de sessie spreekt als odin en duurt ten hoogste
vijftien minuten.

Het antwoord SHALL de bron als URL noemen, onderscheiden wat de bron zegt van
wat de sessie eruit afleidt, en ronduit zeggen wanneer iets niet op te halen
was — een betaalmuur, een pagina die alleen met JavaScript werkt, een site die
weigert, of een videolink die alleen een lege pagina oplevert en geen
transcriptie. Een vage samenvatting van een pagina die niet gelezen kon
worden, is het slechtste mogelijke antwoord.

Waarom dit een type is en geen gereedschap in de chat-agent: de hub blijft
vrij om te antwoorden, en een chat-agent krijgt geen `WebFetch`. Wat op het
web staat, wordt door een vreemde geschreven.

#### Scenario: Een link wordt opgezocht, met bron

- **WHEN** odin een vraag over een link doorzet als `!sessie research …`
- **THEN** komt het antwoord later in hetzelfde kanaal, onder odins naam, met
  de URL waar het vandaan komt

#### Scenario: Wat niet op te halen was, wordt zo gemeld

- **WHEN** de bron een videolink is die geen transcriptie oplevert
- **THEN** zegt het antwoord dat, in plaats van te raden uit de titel

#### Scenario: Een research-sessie schrijft niets

- **WHEN** een research-sessie draait
- **THEN** heeft hij geen schrijvend gereedschap en geen repository als werkmap

### Requirement: Een agent start een sessie alleen vanaf de eerste regel van zijn eigen antwoord

Een markering in het antwoord van een agent (`!sessie …`) SHALL alleen tellen
op de eerste regel van dat antwoord. Een markering verderop, bijvoorbeeld in
geciteerd materiaal, SHALL niets starten. Voor een mens in een kanaal blijft
het zoals het was: die mag de markering onder een zin zetten.

Het verschil is vertrouwen, niet syntaxis. Een agent die het web kan lezen,
kan een pagina lezen waarop `!sessie …` staat. Die regel is door een vreemde
geschreven; het hele antwoord doorzoeken zou die vreemde een sessie laten
starten door geciteerd te worden. Door alleen de eerste regel te lezen wordt
geciteerd materiaal onschadelijk, zonder te hoeven raden wat een citaat is.

#### Scenario: Een geciteerde markering start niets

- **WHEN** het antwoord van een agent halverwege een geciteerde regel
  `!sessie …` bevat
- **THEN** start er geen sessie

#### Scenario: De eigen markering op de eerste regel werkt

- **WHEN** het antwoord van een agent begint met `!sessie wordsworth …`,
  eventueel na witruimte
- **THEN** start die sessie

#### Scenario: Een mens mag de markering onder een zin zetten

- **WHEN** een mens een bericht stuurt met een zin en daaronder `!sessie …`
- **THEN** start die sessie, zoals voorheen
