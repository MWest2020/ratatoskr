# Design: add-chat-native-agents

## Waarom een tweede klasse en niet "alles in habitat"

Habitat-Jobs zijn bewust eenmalig (`backoffLimit: 0`, exit na push) en doof
voor alles buiten env + git. Een gesprek voeren vereist het omgekeerde: een
proces dat een relay-subscription vasthoudt en op mentions reageert. Die twee
vormen mengen zou habitats sterkste invariant ("geen andere invoerkanalen")
slopen. Twee klassen, elk met eigen kooi-principes, is saaier en veiliger dan
één klasse die beide half kan.

## Waarom buzz-acp en geen eigen harnas

`buzz-acp` is upstreams standaard-entrypoint: het houdt het keypair, publiceert
presence, handelt `!shutdown` en idle-reaping af, en start de eigenlijke agent
(o.a. Claude Code) met identiteit en beleid via gereserveerde env-vars die
gebruikersconfig niet kan overschrijven. Zelf bouwen zou dit alles opnieuw
uitvinden. Aandachtspunt: de agent-backend draait onder subscription-auth waar
mogelijk (sub-first-conventie); of `buzz-acp` dat toestaat is een
apply-onderzoeksvraag — zo niet, dan is dat een bewuste uitzondering in dit
design.

## Kooi-principes van deze klasse

Geen K8s-kooi, wél dezelfde lat:

1. **Geen git-push-credentials.** Het deliverable is tekst in kanalen; wil een
   uitkomst code worden, dan gaat die via de normale route (OpenSpec-change →
   habitat-run).
2. **Mandaat buiten bereik.** Het mandaat leeft in boomhuis; de agent-host heeft er
   hooguit een read-only kopie van. Een agent die zijn eigen mandaat, sleutels
   of relay-config kan wijzigen is een hard-fail, net als de kooi-regel in
   habitat.
3. **Eigen host, eigen failure-domain.** Niet in de habitat-namespace, niet op
   de relay-host.
4. **Begrensd bestaan.** Idle-timeout (reaping) en budgetplafond per agent;
   "langlopend" betekent bereikbaar, niet eeuwig brandend.

## Eerste rollen

- **marketing**: schrijft concepten (posts, README-teksten, aankondigingen) in
  `#marketing`; publiceert nooit zelf ergens.
- **architect-sparring**: leest mee via de handbook-MCP (read-only) en denkt in
  `#architectuur` mee over ontwerpen; onderscheidt zich van habitats
  architect-rol (die plant één change in één repo, eenmalig).

## Bewust nog open

Hostkeuze, modelkeuze per rol, en of de agents de handbook-MCP direct mogen
bereiken of alleen meegegeven context krijgen — conversational design met Mark
vóór apply.
