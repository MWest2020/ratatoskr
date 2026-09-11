# Ontwerp: de hernoeming

## Waarom één leesfunctie en geen zoek-en-vervang

**Gekozen:** `chat/instellingen.py` met `lees("URL")` dat eerst `RATATOSKR_URL`
probeert en daarna `BOOMHUIS_URL`. Alle leesplekken gaan door die functie.

**Verworpen: overal `BOOMHUIS_` door `RATATOSKR_` vervangen.** Dat is één
commando en het werkt — tot het moment van uitrollen. Dan draait er een nieuw
image tegen een `.env` die nog de oude namen heeft, en valt de installatie stil
op een lege database-URL of een lege `BOOMHUIS_URL` in uitnodigingslinks. Met de
terugval werkt oud én nieuw, en is de volgorde van uitrollen niet kritisch.

**Verworpen: de oude namen meteen laten vallen na de migratie.** Ze kosten drie
regels en ze zijn de enige terugrolweg. Ze verdwijnen als er een reden is om ze
te laten verdwijnen, niet omdat ze lelijk zijn.

## Het volume is het enige onomkeerbare

Alles hier is terug te draaien behalve één ding: het volume met `auth.db`. Daarom
**kopiëren, niet verplaatsen**, en het oude volume blijft staan tot de nieuwe
kant een paar dagen draait. `docker compose down -v` is de enige knop die dit
weggooit en die staat nergens in het pad.

## Het image krijgt een nieuwe naam, niet een nieuwe tag

**Gekozen:** `ratatoskr-chat` als nieuw pakket, `boomhuis-chat` blijft bestaan.

**Verworpen: het oude pakket hernoemen of weggooien.** Een installatie pint op
`ghcr.io/mwest2020/boomhuis-chat:0.1.1`. Die pin moet blijven werken, anders is
"gepind" een leugen. Het oude pakket krijgt geen nieuwe tags meer; dat is genoeg.

## Wat bewust NIET meegaat in deze ronde

- **De relay heet nog steeds buzz** en het compose-project `buzz-prod`. Dat is
  upstream-software van iemand anders; hernoemen zou alleen verwarring toevoegen.
  Het volume-voorvoegsel blijft daardoor `buzz-prod_`.
- **De handbook-agentdefinities** noemen boomhuis. Die staan onder Marks
  CODEOWNERS en volgen in een eigen PR daar.
- **`BOOMHUIS_APP_TOKEN`** is dood sinds `inloggen-per-persoon` (staat niet meer
  in de live `.env`), maar blijft in de code staan met terugval. Dood spul
  opruimen is een gedragsverandering en hoort in een eigen change, niet
  meeliften op een hernoeming.
