# Design: add-mention-add-agent-ux

## Scope: versturen + lidmaatschap, NIET aanspreekbaarheid

Deze change gaat over het VERSTUREN en het toe-te-voegen LIDMAATSCHAP, niet over of
een agent antwoordt. Zonder geforceerde `--mention` accepteert de relay een bericht
met `@naam` alleen als die naam LID is; is 'ie geen lid → fout
`mention '@X' does not match a current channel member`. We parsen die fout (die de
naam bevat) en bieden een keuze: agent → toevoegen (lid maken), anders → toch
versturen (presentation-only).

**Belangrijk (grens van deze change):** lid worden ≠ antwoorden. Of een agent
reageert bepaalt de listener (`agents/listener.py`): die scopet op de handbook-
`chat.channels` van de agent en triggert op substring-match in de content — hij
kijkt (nog) niet naar relay-lidmaatschap. Aanspreekbaar maken van een toegevoegde
agent (of coordinator overal) is dus een aparte, gekoppelde change: **listener op
lidmaatschap**. Deze change zorgt dat de send lukt en de agent lid ís, als
voorwaarde daarvoor.

## Waarom de vorige `--mention <vaste pubkey>` fout was

Die truc maakte elk @woord presentation-only, maar vereiste dat de meegegeven
pubkey LID van het kanaal was. Geen enkele vaste pubkey is lid van álle kanalen
(mark's geroteerde pubkey is nergens lid, z'n oude alleen in sommige), dus de send
brak in kanalen waar de pubkey niet zat. Vandaar `_a_member_of`: bij force nemen we
een écht bestaand lid van dát kanaal als anker-mention.

## Toevoegen mag vanuit de backend

`/api/channel/add-member` tekent als mark (backend-nsec) — mark kan andere
identiteiten toevoegen (niet zichzelf: self-add faalt op "missing p tag", maar dat
is hier niet aan de orde). Naam→pubkey komt uit de registry via
`roster.agent_pubkey` (case-insensitive, alléén chat-agent/meta-agent — sessies en
mark worden bewust niet aangeboden); een onbekende agent geeft 404, geen stille no-op.

## Afhankelijk van de relay-foutstring

De pop-up-flow herkent een niet-lid-mention aan de relay-fout
`mention '@X' does not match a current channel member`. Wijzigt de relay die
formulering, dan valt de send terug op een gewone error-toast (niet kapot, wel
minder mooi) — veilige degradatie. Een regressietest hierop is vervolgwerk zodra de
backend een test-harness krijgt.

## Meerdere niet-lid-mentions in één bericht

De relay meldt per send maar één ontbrekende mention. Bij bv. `@a @b` (beiden geen
lid) voegt de pop-up @a toe en verstuurt daarna met `force`; @b blijft dan platte
tekst (wordt niet toegevoegd). Bewuste keuze: force = "verstuur het, namen zijn
tekst". Wil je @b óók als lid, noem 'm dan in een volgend bericht. Geen add-lus over
alle mentions — dat is meer machinerie dan de winst rechtvaardigt (KISS).
