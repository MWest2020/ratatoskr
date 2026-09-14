# Change: doorsturen zoals Slack, in plaats van woordelijk napraten

## Why

`add-route-message` (gisteren gearchiveerd) gaf odin een `!route`-marker met één
harde regel: de doorgestuurde tekst moet **woordelijk** in het bericht van de
mens staan. Dat klonk streng en was verkeerd gericht.

Vandaag bleek het twee keer. Eerst deed het ding het helemaal niet — daarover
hieronder. En toen het werkte, paste het niet: odin schreef voor @bouwer een
gecontroleerde analyse van vier securitybevindingen, met duiding en een concrete
opdracht, en dát is wat je wilt doorsturen. Mijn regel had het geweigerd, want er
stond geen woord van Mark in.

Mark: *"en mogelijk gewoon doorsturen zoals in slack?"*

## Wat er ook mis was, en dat is de grotere les

Odin bleef melden: *"ik heb geen tool om zelf in #bouw te posten."* Dat klopte.
`bootstrap.fetch_def` haalt de systeemprompt uit het blockquote onder
`## Chat-facet` en **nergens anders vandaan**. De `## Capabilities`-sectie die ik
in de handbook-definitie zette, staat daarboven en werd dus nooit meegestuurd.
De capability was end-to-end gebouwd behalve op het punt waar hij begint: het
model wist er niet van.

Eén laag dieper zat dezelfde fout nog een keer: de prompt toont berichten als
`wie: inhoud`, zonder id. Ook met de juiste instructie had odin niets kunnen
aanwijzen.

## What Changes

- **`!forward #<kanaal> <bericht-id>` plus een eigen notitie.** Je stuurt een
  BESTAAND bericht door; de listener haalt de inhoud zelf op. De agent schrijft
  het citaat dus niet — hij wijst het aan. Dat is **strenger** dan de vorige
  versie, niet losser: een woordelijkheidscontrole toetst of een kopie klopt,
  dit maakt kopiëren overbodig. Een verzonnen citaat kan niet.
- **De eigen notitie mag**, en staat eronder met de naam van de doorstuurder
  erbij, zodat niemand hem voor het origineel aanziet.
- **`!route` blijft werken als alias.** Een agent die de oude vorm geleerd heeft
  moet niet stil falen omdat ik het woord veranderd heb.
- **`prompts.route_clause(cfg)`** vertelt het de agent, gegenereerd uit zijn
  eigen `routes` — zodat de aankondiging niet kan afdrijven van het mandaat.
  Geen routes, geen zin.
- **Bericht-ids in de prompt**, alleen voor een agent die mag doorsturen. Voor de
  rest is het ruis in elke beurt.

## Wat er NIET verandert

Nog steeds alleen kanalen uit `agent.chat.routes` in de handbook-definitie,
fail-closed bij leeg of verkeerd type. Nog steeds alleen een bericht uit het
kanaal waar de agent is aangesproken — hij kent de rest niet. Nog steeds een
bronvermelding uit de code die de agent niet kan weglaten. En een weigering gaat
nog steeds naar #escalatie én naar het bronkanaal.
