# Design: reown-channels-to-orchestrator

## Besluit 1 — mede-eigenaarschap, niet recreëren

De proposal hield beide open ("relay-ondersteuning uitzoeken; anders recreëren +
leden opnieuw"). Uitgezocht en live gemeten: `buzz channels add-member --role
owner` werkt, en de relay staat **meerdere eigenaren** toe. Een "overdracht" is
dus een *toevoeging*: mark blijft eigenaar, de orchestrator komt erbij.

Dat is precies genoeg voor het doel. Het doel was nooit "mark mag er niet meer
bij", maar "geautomatiseerd kanaalbeheer heeft de mens-sleutel niet nodig".
Bewijs: `set-channel-descriptions.py` zet nu met de orchestrator-sleutel de
beschrijving op **alle vijftien** kanalen, ook op de vijf die eerder faalden.

Mark als eigenaar wegnemen is bewust niet gedaan: dat zou hem admin-rechten op
zijn eigen kanalen kosten, zonder dat er een probleem mee opgelost wordt.

**Verworpen: recreëren.** Dat kost de geschiedenis van het kanaal (#red-team en
#netnl hebben inhoudelijke overdracht), vergt het opnieuw toevoegen van alle
leden, en geeft elk kanaal een nieuw id — waarna `channels.yml`, `jobs.yml`, de
listener en elk pinned document mee moeten. Duur en breekbaar, voor een probleem
dat de relay al oplost.

## Besluit 2 — fail-closed zonder orchestrator-sleutel

Ontbreekt `BUZZ_ORCHESTRATOR_KEY`, dan geeft kanaalbeheer **503 met een leesbare
melding**; het valt niet terug op de procesidentiteit.

**Verworpen: terugvallen op marks sleutel.** Dat is precies het gedrag dat deze
change wegneemt, en een stille terugval is erger dan het huidige gedrag: je zou
denken dat beheer agent-getekend is terwijl het dat niet is. Een zichtbare 503 is
een deployvraag; een stille terugval is een auditgat.

**Verworpen: de sleutel uit SOPS lezen in de backend.** De chat-backend is
stdlib-loos en heeft geen age-sleutel; hem er wél geven maakt van een
lees-en-post-backend een tweede secret-houder. Eén env-var uit `chat.env`, net
als de bestaande nsec, is het saaie pad dat al gebruikt wordt.

## Besluit 3 — marks sleutel alleen in één script, alleen voor één subcommando

`orchestrator/reown-channels.py` is de enige plek die marks nsec aanraakt, en
uitsluitend voor `channels add-member --role owner`. Idempotent (een kanaal dat
de orchestrator al bezit wordt overgeslagen), met `--dry-run`, en het verifieert
de nieuwe eigenaar ná de wijziging in plaats van de exitcode te geloven.

`ping.sh` blijft marks identiteit weigeren: posten als de mens blijft verboden.
Het onderscheid is bewust — eigenaarschap overdragen is een eenmalige
beheerhandeling, je voordoen als de mens is impersonatie.
