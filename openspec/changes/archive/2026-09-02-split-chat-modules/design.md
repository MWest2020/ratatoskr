# Design: split-chat-modules

Refactor zonder functionele wijziging (archiveer met `--skip-specs`; geen
capability-delta). Niet-voor-de-hand-liggende keuzes:

## 1. server.py → buzzcli.py langs de HTTP/data-grens

**Keuze:** alles wat via buzz-cli met de relay praat (kanalen, leden, counts,
roster) gaat naar `buzzcli.py`; `server.py` houdt routing + PWA-serving.

**Verworpen:** per-endpoint-modules of een framework. De grens data-vs-HTTP is de
natuurlijke naad, `github.py` bestond al zo, en het houdt beide bestanden ≤ 200
zonder een web-framework toe te voegen (KISS, geen nieuwe dependency).

## 2. index.html → app.css + app.js + app-ui.js als classic scripts

**Keuze:** twee losse `<script>`-bestanden (geen ES-modules), die de global scope
delen; `app-ui.js` laadt als laatste en draait de init.

**Verworpen:** (a) ES-modules (`type=module`) — dan moet elke functie ge-export/
import worden en verandert de (bewust globale) opzet ingrijpend, meer diff dan een
refactor rechtvaardigt; (b) één groot app.js — dat blijft > 200 regels. Twee
classic scripts delen de global lexical scope, dus de bestaande functies/vars
werken ongewijzigd zolang de init in het laatst-geladen bestand staat.
