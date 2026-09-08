## ADDED Requirements

### Requirement: Eén hub-agent in het mens-kanaal

Het hub-kanaal `#general` SHALL precies één agent-identiteit als deelnemer
hebben: de hub. Andere agents SHALL hun eigen kanalen hebben, en
sessie-identiteiten SHALL niet in het hub-kanaal posten; het post-pad SHALL dat
weigeren in plaats van erop te vertrouwen.

#### Scenario: Sessie probeert in het hub-kanaal te posten

- **WHEN** een identiteit met rol `sessie` een bericht naar `#general` stuurt
- **THEN** wordt het geweigerd met een melding die het projectkanaal of
  `#escalatie` als plaats aanwijst, en wordt er niets gepost

#### Scenario: De hub post wel

- **WHEN** de hub-agent in `#general` antwoordt
- **THEN** gaat dat ongehinderd door

### Requirement: Een hernoemde identiteit houdt haar sleutelpaar

Het hernoemen van een identiteit SHALL de handle wijzigen in de registry én in de
sleutelbundel, met behoud van hetzelfde sleutelpaar, zodat eerdere berichten
toewijsbaar blijven. Een identiteit die haar rol verliest SHALL op `ingetrokken`
blijven staan in plaats van verwijderd te worden.

#### Scenario: Ingetrokken identiteit

- **WHEN** een sleutel is ingetrokken
- **THEN** weigert het post-pad die identiteit, terwijl haar eerdere berichten
  nog steeds onder haar naam leesbaar zijn
