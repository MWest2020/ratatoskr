# Ontwerp: het werk-overzicht

## Een bord vóór een graaf

**Gekozen: kolommen, en pas daarna een graaf.**

Een graaf is mooi en zegt zelden waar je aandacht heen moet. Wat je wilt weten is
"wat beweegt, wat zit vast", en dat is een volgorde-vraag: iets staat ergens in
een keten en het staat er te lang. Kolommen beantwoorden dat direct; een graaf
vraagt eerst dat je 'm leest.

De graaf verdwijnt niet — hij wordt een **tweede weergave van dezelfde kaarten**.
Daarom legt deze change de gegevens vast (kaarten met repo, status, ouderdom,
relaties) en niet een bordspecifiek formaat. Een graaf later is dan een
view, geen tweede verzameling.

**Verworpen: meteen de graaf.** Dat is de leuke versie bouwen vóór de nuttige,
en je zit daarna vast aan een datamodel dat om knopen en randen gaat in plaats
van om werk.

## Eén producent buiten de container

**Gekozen: een terugkerende taak op agent-lxc schrijft `board.json` in het
datavolume; de chat serveert dat bestand.**

De gegevens liggen niet waar de chat draait. OpenSpec-changes staan in acht
git-clones op agent-lxc, de lopende werksessies in het geheugen van de listener,
PR's bij GitHub. De chat draait in een container met de PWA en de buzz-CLI, en
dat moet zo blijven: hij is expres dependency-loos.

Dit is hetzelfde patroon als `knowledge/_live.md` (door `orchestrator/live.py`
geschreven, door de listener gelezen) — dat werkt al maanden en niemand hoeft
het uit te leggen.

**Verworpen: de chat haalt alles zelf op.** Dan moet de container clones hebben,
`gh` hebben, en netwerktoegang naar GitHub — en elke traagheid daar wordt een
trage app. Het is ook precies het soort koppeling waardoor `/api/overview` 502
gaf toen de relay onbereikbaar was.

**Verworpen: het bord uit chatberichten afleiden.** De standup-job post al tekst;
daar een bord van terugrekenen is een parser op proza bouwen. De bron van de
standup is dezelfde data — die lezen we direct.

## Ouderdom is het signaal, niet het aantal

**Gekozen: elke kaart draagt hoe lang hij in zijn huidige kolom staat, en het
bord markeert wat daar te lang staat.** Drempels per kolom, in de config, niet in
de code.

Een bord dat alleen toont *dat* er twaalf dingen open staan, vertelt je niets
wat de standup niet ook zegt. Wat je niet uit tekst haalt is dat kaart #71 al
drie dagen op review wacht terwijl de rest doorstroomt.

**Verworpen: WIP-limieten.** Die horen bij een team dat werk aan elkaar geeft.
Hier is één mens met een zwerm agents; de limiet die telt is zijn aandacht, en
die dwing je niet af met een getal per kolom.

## Wat er NIET in komt

- **Slepen.** Een kaart verplaatsen zou betekenen dat het bord de waarheid is.
  Git is de waarheid; het bord is een spiegel. Een kaart verplaats je door een
  PR te mergen of een change te archiveren.
- **Habitat-jobs live.** Die staan in het cluster en vergen `kubectl` in de
  producent. Kan later; de kaartvorm is er al op voorbereid.
- **Historie.** Geen doorlooptijd-statistiek, geen grafieken over de tijd. Dat is
  een meetinstrument, en dit is een aandacht-instrument.
