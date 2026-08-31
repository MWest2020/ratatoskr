# Design: add-unread-counter

Niet-voor-de-hand-liggende keuzes met verworpen alternatieven (CLAUDE.md-eis).

## 1. Leesstatus per device (localStorage), niet server-side gedeeld

**Keuze:** "gezien" leeft in de browser (`localStorage.bh_seen`), per apparaat.

**Verworpen:** server-side, cross-device gedeelde read-state. De webchat post
namens één server-side identiteit (`mark`) en heeft geen per-gebruiker-sessie of
login (zie de security-review 2026-08-30 + `chat/server.py`). Er is dus geen
principal om read-state aan te hangen, en "ongelezen" is inherent per apparaat
(je telefoon weet niet wat je op desktop las). Server-side zou nieuwe state,
identiteit en synchronisatie introduceren voor weinig winst — tegen KISS.

## 2. Cache-TTL >= poll-interval + single-flight-lock

**Keuze:** `/api/overview` cachet 15s (client polt 12s) achter een lock; bij een
miss doet één thread de buzz-fan-out, de rest krijgt het verse resultaat.

**Verworpen:** (a) TTL < poll (6s) — dan mist een enkele client de cache bij elke
poll, precies wat de cache moest voorkomen; (b) geen lock onder
`ThreadingHTTPServer` — dan draaien N gelijktijdige clients allemaal de volledige
fan-out (N buzz-subprocessen per kanaal), een thundering herd.

## 3. Baseline op eerste overview (verse install = alles gelezen)

**Keuze:** een kanaal zonder `seen`-entry krijgt bij de eerste overview zijn
huidige count als baseline; badges tellen pas nieuwe activiteit daarná.

**Verworpen:** hele historie als ongelezen tonen bij een verse install — dat geeft
een muur van badges voor berichten die je nooit als "nieuw" hebt ervaren.
