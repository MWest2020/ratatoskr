---
status: draft
last_reviewed: 2026-08-29
---

# Ratatoskr — de pitch

*Grondstof voor een blogpost, talk-abstract of README-voorwoord. Ratatoskr zelf
blijft privé en tailnet-only; wat je naar buiten brengt is het patroon, niet de
draaiende dienst.*

## In één zin

Eén mens stuurt een zwerm AI-agents aan zoals je een team aanstuurt: via chat —
kanalen, mentions, threads — terwijl git de waarheid blijft en de agents die
code raken in een dichte kooi draaien.

## Het probleem

Wie serieus met agents werkt, heeft al snel executie (agents die code
schrijven) en kennis (docs, specs, inventaris). Wat ontbreekt is een *plek*. De
inbox is een tmux-pane: een escalatie bestaat alleen als je toevallig
aangekoppeld zit, een reviewer-bevinding bereikt nooit de bouwer, en rollen
zonder code-deliverable — marketing, architectuur-sparring, coördinatie —
hebben geen plek om te bestaan. Je bent geen dirigent; je bent een polling-loop.

## De aanpak

Ratatoskr maakt chat de control-plane, zonder aan de harde grenzen te tornen:

- **Chat als control-plane.** Een zelf-gehoste [buzz](https://github.com/block/buzz)-relay
  (Nostr) met kanalen voor mens én agents. Je praat met `@bouwer` in `#bouw`,
  droppt een idee bij `@coordinator` in `#general`, en de digest-jobs posten
  vanzelf in `#proposals` en `#news_from_zettelkast`.
- **Git blijft de waarheid.** Verdicts, audit-spoor en run-rapporten leven in
  git. Chat is coördinatie en spiegel — nooit gezaghebbende state.
- **De kooi blijft dicht.** Agents die code wijzigen draaien als eenmalige,
  gekooide Jobs zonder relay-toegang. Alleen langlopende conversatie-agents
  praten in de chat. Twee klassen, één grens ertussen.
- **Eén bron van waarheid voor wie een agent ís.** Elke agent-definitie leeft
  canoniek in één handboek-repo, met een chat-facet en een executie-facet. Een
  drift-gate dwingt af dat de gekooide uitvoerder en de chattende persona
  dezelfde zijn. Een bouwer is overal dezelfde bouwer.
- **Sub-first, geen API-sleutel.** De agents rijden op een `claude -p`-listener
  op het abonnement — geen aparte API-key-kostenpost om de zwerm te laten praten.

## Wat het bewijst

Je kunt een "one-man army" zijn zonder je governance op te geven. De dingen die
mensen bang maken aan agent-zwermen — ongecontroleerde uitvoering, agents die
hun eigen mandaat herschrijven, geen audit-spoor — worden hier niet met
vertrouwen opgelost maar met structuur: een dichte kooi, git-als-waarheid, één
bron van waarheid met een drift-gate, en een closed relay met een eigen
sleutelpaar per identiteit.

## Status

Beta (v0.1). De relay, de webchat (Slack/Telegram-achtig, kanalen maken en
verwijderen in de app), zes chat-agents uit de handboek-registry, recurring
digest-jobs en de doel→dispatch-brug tot de rand van de kooi draaien
reboot-vast op het tailnet. De laatste cluster-fire van de brug is nog
gesuperviseerd. Rome is niet in één dag gebouwd — maar Ratatoskr staat.
