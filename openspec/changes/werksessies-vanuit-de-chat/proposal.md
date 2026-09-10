# Change: werksessies vanuit de chat

## Why

Mark vroeg het zo: "ik had ooit gevraagd voor de optie dat odin zelf claude
sessies kon opspinnen. er was een tmux sessie die precies deed wat ik hier
vroeg: zettelkast shared links analyseren. ik moet dat in boomhuis kunnen."

Odin zelf meldde de reden dat het niet gaat, in zijn eigen woorden in #general:
"LIMITATIE: ik heb geen tool-toegang tot een tmux-sessie op agent@agent-lxc".
Dat klopt, en het is geen bug maar het ontwerp: een chat-beurt is één
`claude -p`-aanroep van hoogstens 150 seconden, met `Read/Grep/Glob` begrensd
tot de werkboom en een gestripte omgeving. Prima voor een gesprek, te klein
voor werk.

Wat vandaag wél bestaat dekt het gat niet:

- **`jobs/`** draait langere `claude -p`-runs, maar alleen op een timer, met een
  vaste prompt uit `jobs.yml` en zónder gereedschap (kale prompt + `context_cmd`).
  Je kunt er niets vanuit een gesprek aan vragen.
- **`habitat-bridge`** dispatcht wél op verzoek, maar naar de kooi: een
  rol-run die een branch en een PR oplevert, met Mark als poortwachter per
  dispatch. Voor "lees deze twaalf clips en zeg wat eruit moet komen" is dat het
  verkeerde gereedschap — er komt geen code uit, en een mens-gate per leesopdracht
  maakt de hele optie zinloos.

Er ontbreekt dus één ding: een **langere, gereedschap-gebruikende, LEZENDE run
die vanuit een kanaal gestart wordt en in datzelfde gesprek terugrapporteert.**

## What changes

- **Werksessies** als nieuwe mogelijkheid van de listener. Een sessie is een
  losse `claude -p`-run met een eigen werkmap, eigen toolset, eigen model en
  een eigen tijdbudget (minuten, geen seconden), die zijn voortgang en zijn
  resultaat in het startende kanaal post.
- **Sessietypes staan in git**, niet in een prompt: `agents/sessies.yml`
  declareert per type de werkmap, de tools, het model, het tijdbudget, wie het
  type mag starten en welke identiteit het resultaat post. Een agent kiest
  alleen wélk type en geeft de opdracht in vrije tekst mee.
- **Starten gebeurt met een marker**, net als bij de brug: een regel
  `!sessie <type> <opdracht>` in een bericht van een gemachtigde starter, of in
  het antwoord van een gemachtigde agent. De listener is het enige dat op die
  regel handelt; de regel zelf wordt uit het geposte antwoord geknipt.
- **Eerste type: `zettelkast`** — leest de vault (`sources/`, `wiki/`,
  `journal/`), mag een gedeelde link ophalen, en rapporteert wat er met de
  gedeelde clips zou moeten gebeuren. Precies wat die tmux-sessie deed.
- **Lezend, en dat is de grens.** Een werksessie krijgt nooit `Write`, `Edit`,
  `Bash` of push-rechten. Alles wat een repo verandert blijft via een
  OpenSpec-change en een habitat-run lopen; de brug en zijn poortwachter blijven
  ongewijzigd.

## Impact

- Nieuw: `agents/sessies.py`, `agents/sessies.yml`, `agents/relay.py`
  (relay-I/O uit `listener.py` gelicht zodat die onder de 200 regels blijft),
  `agents/test_sessies.py`.
- Gewijzigd: `agents/listener.py` (start + oogst per tick), `agents/README.md`.
- Spec: nieuwe capability `werksessies`. `habitat-bridge` en
  `chat-native-agents` blijven ongewijzigd — een werksessie is expliciet géén
  dispatch en verandert niets aan de kooi.
