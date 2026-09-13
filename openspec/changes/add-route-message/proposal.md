# Change: odin mag de woorden van de mens doorsturen naar een ander kanaal

## Why

Mark in #architectuur, 2026-09-13: *"@odin zeg het tegen bouwer. Jij bent hub,
bouwer is spoke."* Dat kon odin niet. Een agent antwoordt alleen in het kanaal
waar hij is aangesproken, en odin weigerde terecht het zichzelf te geven:

> "Alles kunnen wat je zegt" is precies wat de kooi en het hub/spoke-ontwerp
> uitsluiten — dat verander ik niet stiekem via een tool-aanroep, dat is een
> mandaatswijziging die door de handbook moet, met jou als reviewer.

Dat is de juiste weigering, en dit is de change die eruit volgt. Bouwer maakte
er in #bouw een voorstel van en zette er één voorwaarde bij: apply pas ná een
security-run op twee punten — de payload versus een instructie aan de agent, en
een bronvermelding die vastligt. Die twee zijn hieronder niet beloofd maar
afgedwongen.

Het hub/spoke-model werkt alleen als de hub iets kán doorgeven. Zonder dit moet
Mark elk bericht twee keer typen, in twee kanalen, en dan is de hub een extra
stap in plaats van een doorgeefluik.

## What Changes

- **Een marker, geen tool.** `!route #<kanaal>` in het antwoord van een agent,
  dezelfde vorm als `!sessie`. De agent krijgt geen nieuw gereedschap, geen
  tweede sleutel en geen MCP-oppervlak: hij schrijft een regel, de **listener**
  doet het. Een model met een tool beslist zelf wanneer hij hem gebruikt; een
  marker die de listener nakijkt niet.
- **Letterlijk, mechanisch afgedwongen.** De doorgestuurde tekst MOET woordelijk
  voorkomen in het bericht van de mens dat deze beurt opriep (witruimte
  genormaliseerd). Zo niet: er gaat niets weg en het gaat naar #escalatie. Dit is
  het verschil tussen "de agent belooft niet te interpreteren" en "de agent KAN
  niet interpreteren" — en alleen het tweede blijft waar als het model verandert.
- **De bronvermelding komt uit de code.** Wie, uit welk kanaal, welk bericht-id.
  De agent schrijft die regel niet en kan hem niet weglaten of vervalsen. De
  payload staat in een blockquote, zodat voor de ontvangende agent zichtbaar is
  waar andermans woorden beginnen en ophouden.
- **Het recht staat in de handbook**, niet in de listener en niet in een prompt:
  `agent.chat.routes` is de lijst kanalen waar deze agent naartoe mag. Afwezig,
  leeg of van het verkeerde type = niets doorsturen. Fail-closed.
- **Een weigering is zichtbaar**, in #escalatie én in het bronkanaal. Stil
  weigeren is hoe je erachter komt dat niemand het merkt.

## Impact

- Nieuw: `agents/routing.py` + `agents/test_routing.py`.
- Nieuw: `agents/session_wiring.py` + test — `listener.py` stond op 199 van de
  200 regels, dus de sessie-koppeling gaat eruit zoals destijds bij
  `chat/server.py`. Die code was alleen indirect getest en krijgt nu een eigen
  suite.
- Gewijzigd: `agents/listener.py` (één aanroep), `agents/bootstrap.py` (leest
  `routes` uit de definitie).
- Handbook: `docs/agents/odin.md` krijgt `chat.routes: [bouw]` en een sectie
  *Capabilities*. **Dat is Marks poort** (CODEOWNERS), aparte PR.
- Handmatig, één keer: odin moet relay-lid zijn van #bouw, anders weigert de
  relay de post. `orchestrator/add-member.py --chan bouw --name odin --role bot`.

## Wat dit NIET is

Geen dispatch, geen shell, geen schrijfrecht. De agent verzint niets en besluit
niets; hij wijst aan welke woorden van de mens waarheen gaan. Wil je dat een
agent wél zelf iets formuleert in een ander kanaal, dan is dat een andere change
met een ander gesprek.
