# Change: listener-membership

## Why

Een @mention naar een agent blijft in veel kanalen onbeantwoord (bv. #red-team,
#standup). Oorzaak: de listener bepaalt wie reageert puur op de HANDBOOK-
`chat.channels` van de agent — niet op relay-lidmaatschap. De coordinator staat
in de handbook op `channels: [general]`, dus ook al is 'ie via de operator-backfill
lid van elk kanaal (change `add-mention-add-agent-ux`), de listener target 'm alleen
in #general. Netto: "coordinator in elk kanaal" en agents-toevoegen-via-de-pop-up
maken een agent wél LID maar niet AANSPREEKBAAR — de gekoppelde helft ontbreekt.

Daarnaast poll't de listener alleen de kanalen uit het statische `channels.yml`.
Een kanaal dat via de webchat wordt aangemaakt staat daar niet in, dus daar wordt
sowieso niets opgepikt.

## What Changes

- **Routeren op relay-lidmaatschap.** Een agent reageert op `@handle` in kanaal C
  als 'ie handbook-gescopt is op C **of** relay-LID is van C. Zo maakt lid-worden
  (pop-up / coordinator-default / backfill) een agent daadwerkelijk aanspreekbaar,
  zonder de handbook-def te hoeven wijzigen.
- **Live kanaal-set.** De poll-lijst komt uit `buzz channels list` (alle open
  kanalen), met `channels.yml` als vangnet — nieuwe kanalen worden vanzelf gepoll'd.
- Lidmaatschap en kanaal-lijst worden kort gecachet (~60s) zodat de poll-lus de
  relay niet hamert.
- **Ongewijzigd:** thread-vervolg (laatst-actieve agent praat door), de npub-guard
  bij spawnen, en dat def-kanalen blijven werken (union, geen vervanging).

**Grens:** dit gaat over WIE reageert (aanspreekbaarheid). Een zichtbare
"denkt na…"-indicator tijdens het verwerken is een aparte, volgende change.

## Impact

- `agents/listener.py` (routing op lidmaatschap + live poll-set), nieuw
  `agents/topology.py` (relay-kanalen + leden + pure `is_scoped`), `agents/prompts.py`
  (context/prompt-bouwers + `mentioned`), `agents/bootstrap.py` (yaml + handbook-def)
  en `agents/providers.py` (provider-naad) — uitgesplitst zodat listener.py ≤200
  regels blijft; `agents/test_topology.py` dekt de pure logica.
- Gedrag: agents antwoorden nu op een @mention in élk kanaal waar ze lid zijn
  (thread-vervolg blijft def-kanaal-only); leesbaar via de bestaande listener-logs.
  Additief, geen migratie.
