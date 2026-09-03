# Design: add-mention-add-agent-ux

## De relay is al de juiste bron van waarheid

Zonder geforceerde `--mention` doet de relay precies wat we willen: `@agent` dat lid
is → geaccepteerd + getriggerd (`mention_pubkeys`); `@naam` dat geen lid is → fout
`mention '@X' does not match a current channel member`. We parsen die fout i.p.v.
'm te onderdrukken — de fout bevat de naam, dus we weten wie en waar.

## Waarom de vorige `--mention <vaste pubkey>` fout was

Die truc maakte elk @woord presentation-only, maar vereiste dat de meegegeven
pubkey LID van het kanaal was. Geen enkele vaste pubkey is lid van álle kanalen
(mark's geroteerde pubkey is nergens lid, z'n oude alleen in sommige), dus de send
brak in kanalen waar de pubkey niet zat. De registry-gedreven pop-up lost dat
structureel op: je voegt de échte agent toe.

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
