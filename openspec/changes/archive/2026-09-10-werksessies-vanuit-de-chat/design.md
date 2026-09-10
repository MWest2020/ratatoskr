# Ontwerp: werksessies vanuit de chat

Alles wat hier staat is een keuze die niet vanzelf spreekt, mét het alternatief
dat is afgevallen.

## 1. Een genoemd type uit git, geen shell voor de agent

**Gekozen:** een sessie is altijd een type uit `agents/sessies.yml`. Dat bestand
bepaalt de werkmap, de tools, het model, het tijdbudget en wie mag starten. De
agent kiest het type en levert de opdracht als vrije tekst.

**Verworpen: odin een `Bash`-tool geven.** Dat is de directe lezing van "zelf
sessies opspinnen", en het is precies de verkeerde. De listener draagt de nsec
van elke agent in zijn omgeving; `providers.agent_env()` bestaat omdat één
geslaagde prompt-injectie anders genoeg is om die sleutels te lezen. Een agent
met shell op agent-lxc maakt die hele filter zinloos, en het breekt de
invariant "odin maakt of wijzigt zelf niets" uit zijn eigen mandaat. Met een
genoemd type staat de volledige verzameling van wat een sessie kán doen in git,
te reviewen in één bestand, en kiest het model alleen nog uit die verzameling.

**Verworpen: een MCP-server als taakinvoer.** Voor agents geldt: skills als
per-agent subset, geen MCP (besluit agent-runtime). Een MCP-server erbij zou
een tweede, niet-geauditeerde invoerweg zijn voor precies dezelfde functie.

## 2. Marker in de tekst, geen nieuw protocol

**Gekozen:** `!sessie <type> <opdracht>` als losse regel, herkend door de
listener, en uit het geposte antwoord geknipt.

**Verworpen: een tool die de agent aanroept.** Dat vereist een tool-server, een
tweede kanaal en een tweede vorm van authenticatie. De marker gebruikt de naad
die er al is (`claude -p` levert tekst), en de brug (`!dispatch`) heeft
hetzelfde patroon al bewezen. Wie mag starten wordt niet aan de tekst ontleend
maar aan de Nostr-afzender: de listener kent de schrijver al via
`identities.yml`, dus vervalsing vergt een sleutel, niet een regel tekst.

**Waarom de marker uit het antwoord geknipt wordt:** een geposte `!sessie`-regel
zou bij de volgende passage opnieuw gelezen kunnen worden, en agent-berichten
zijn zichtbaar voor iedereen in het kanaal. Knippen maakt van de marker een
instructie die precies één keer telt.

## 3. Lezen mag, schrijven niet

**Gekozen:** een sessie krijgt uitsluitend lezende tools (`Read`, `Grep`,
`Glob`, en per type eventueel `WebFetch`), pad-begrensd tot de werkmap via
`providers.scoped()`, in een gestripte omgeving (`providers.agent_env()`).
`Write`, `Edit`, `Bash`, `Task` en `WebSearch` staan expliciet in de deny-lijst.

**Verworpen: sessies ook laten schrijven.** Dan wordt de werksessie een
tweede, ongepoorte weg naar dezelfde uitkomst als een habitat-run, en is de
poortwachter uit `habitat-bridge` in de praktijk optioneel geworden. De
scheiding die blijft: **lezen en oordelen mag zonder gate; iets veranderen
loopt via een change en de kooi.** Dat is ook wat de sessie zelf moet
opleveren — een voorstel, geen commit.

**Risico dat hierbij hoort en niet verdwijnt:** `WebFetch` haalt tekst op die
niemand heeft gereviewd, en die tekst komt in het contextvenster van de sessie.
Prompt-injectie vanaf een gedeelde pagina is daarmee reëel. Wat het begrenst:
de sessie heeft geen schrijfrechten, geen shell, geen sleutels in zijn
omgeving, en zijn hele opbrengst is tekst in een kanaal dat Mark leest. Wat het
niet begrenst: de sessie kan onzin of gestuurde tekst rapporteren. Daarom is de
opbrengst een voorstel voor een mens en nooit een handeling.

## 4. Niet-blokkerend, met de looptijd als bestand

**Gekozen:** de sessie start losgekoppeld (`start_new_session=True`), stdout
gaat naar een runbestand, en de listener leest per tick het nieuwe stuk van dat
bestand. Voortgang (welke tool, welk pad) verschijnt tussentijds in de thread;
het `result`-event levert het eindantwoord, de kosten en het aantal beurten.

**Verworpen: de sessie in de pollus draaien** zoals een gewone beurt. Een
chat-beurt van 150 seconden bevriest de listener al merkbaar; een sessie van
vijftien minuten zou het hele boomhuis stilzetten voor iedereen.

**Verworpen: een aparte daemon met een wachtrij.** Meer bewegende delen dan het
probleem groot is: er draaien er hoogstens twee tegelijk, en de listener tikt
toch al elke vijf seconden. Het runbestand ís de wachtrij-status, en het
overleeft een herstart van de listener zodat een lopende sessie zichtbaar blijft.

## 5. Grenzen die het ding stilzetten

Per type een `max_seconden` (default 900) — daarna wordt de procesgroep gedood
en post de sessie dat hij is afgekapt. Globaal hoogstens `max_gelijktijdig`
sessies (2), en per starter hoogstens één. Zonder die laatste regel kan een
agent die in een lus praat elke beurt een nieuwe sessie beginnen.

Een afgekapte of gefaalde sessie meldt dát, met de reden. Stil niets posten is
verboden: dan leest het kanaal een storing als "er was niets te melden" — het
zelfde false-clear-risico dat in `run-job.py` al benoemd staat.

## 6. Wie mag starten staat bij het type, niet in de handbook

**Gekozen:** `starters: [odin, mark]` per type in `agents/sessies.yml`.

**Verworpen: een `sessies:`-veld in de handbook-agentdefinitie.** Dat is Marks
CODEOWNERS-gate en vergt dus een handbook-PR per nieuw type, terwijl de
interessante vraag ("wat mag dit type doen, en wie mag het aanzetten") dan over
twee repo's verspreid staat. Bij het type houdt het één reviewbaar bestand:
wat het type mag én wie het mag aanroepen, naast elkaar.
