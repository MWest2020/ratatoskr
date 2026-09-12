# Ontwerp: schrijvende werksessies

## Waarom de oorspronkelijke grens te ruim was

`werksessies-vanuit-de-chat` zei: lezen mag zonder poort, veranderen loopt via
een change en de kooi. Dat klopte voor *mergen* en het klopte niet voor
*voorstellen doen*. Een pull request verandert niets — hij vraagt iets. Tussen
"de agent mag niets aanraken" en "de agent mag naar main pushen" zit precies wat
hier al maanden werkt: een branch en een PR.

**Gekozen: schrijven mag, mergen niet.** De grens verschuift van "geen
schrijfrechten" naar "geen push naar main, geen merge".

**Verworpen: alles via de habitat-kooi.** Dat is de zwaarste weg (K8s-job,
gepind image, credentials verversen) voor werk dat vaak uit drie bestanden en een
test bestaat. De kooi blijft waar hij goed in is; dit is de lichte weg ernaast,
met een PR als uitkomst in plaats van een branch in een cluster.

**Verworpen: lezende sessie + een mens die het overtypt.** Dat is wat er nu
gebeurt en het is precies de stap die Mark vier keer heeft gevraagd weg te halen.

## Een hek, geen belofte

**Gekozen: een `pre-push`-hook in de worktree die alleen de eigen branch
doorlaat.** De sessie krijgt `Bash` (anders geen git, geen tests), en dan is
"push niet naar main" in een prompt niets waard: alles wat in de context komt kan
die prompt sturen — een issue-tekst, een README, een fetch.

De hook staat in de worktree, wordt door de starter geschreven vóór het proces
begint, en de sessie kan hem niet zinvol weghalen zonder dat het in de diff en in
het runbestand staat.

**Verworpen: `git config remote.origin.pushurl` op iets doods.** Dan kan de
sessie ook zijn eigen branch niet pushen, en dus geen PR openen.

**Verworpen: credentials weglaten.** Zonder token geen PR. En een sessie zonder
enige schrijfweg naar buiten is weer een lezende sessie.

## Een eigen worktree, altijd vers

**Gekozen: elke schrijvende sessie krijgt `git worktree add` van `origin/main`
op een nieuwe branch `session/<type>-<requester>-<ts>`, in een eigen map buiten
alle draaiende checkouts.**

Waarom niet in een bestaande map: `~/ratatoskr-listener` draait de listener en
`/opt/...` draait de chat. Een sessie die daarin schrijft, verbouwt zichzelf
tijdens het werk. Gemeten waarom dit ertoe doet: er draaiden ooit twee listeners
omdat een herstart uit twee verschillende bomen kwam.

De map blijft na afloop staan. Een opgeruimde worktree is een verdwenen bewijs;
opruimen is een aparte handeling met een eigen besluit.

## Wie mag dit

**Gekozen: `writes: true` staat per TYPE in `sessies.yml`, en de starters van dat
type zijn een aparte lijst.** Een agent die `zettelkast` mag starten, mag daarmee
niet automatisch `build` starten.

De machtiging blijft verder zoals hij is: starter én aanvrager op `starters`,
limiet per aanvrager. Een schrijvende sessie krijgt een ruimer tijdbudget
(standaard een uur) omdat bouwen met tests nu eenmaal langer duurt dan lezen.

## Wat dit NIET doet

- **Niet mergen.** De sessie opent een PR en stopt. Wie merget is een mens of,
  binnen de bestaande afspraken, een agent met dat mandaat.
- **Niet pushen naar `main`.** Hek, zie boven.
- **Niet in de kooi komen.** `habitat-bridge` en zijn poortwachter blijven
  ongewijzigd; dit is een andere weg met een ander doel.
- **Geen secrets.** De omgeving blijft gestript (`providers.agent_env`), dus geen
  nsec, geen age-key. Wat de sessie nodig heeft om een PR te openen komt uit de
  omgeving van de starter, niet uit de repo.
