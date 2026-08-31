# Tasks: split-chat-modules

- [x] 1.1 `chat/server.py` gesplitst: de buzz/relay-datalaag → `chat/buzzcli.py`;
      server.py houdt routing + statische serving + main. Beide ≤ 200 regels.
- [x] 1.2 `chat/index.html`: inline `<style>` → `app.css`, inline `<script>` →
      `app.js` + `app-ui.js` (classic scripts, gedeelde global scope). index.html
      is nu een dunne shell. Server serveert de nieuwe assets; sw.js cachet ze.
- [x] 1.3 Geen functionele wijziging: sed-extractie behoudt de code exact. Import
      + JS-syntax geverifieerd; live-smoke op de VM vóór merge.
