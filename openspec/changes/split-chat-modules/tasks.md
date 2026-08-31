# Tasks: split-chat-modules

- [x] 1.1 `chat/server.py` gesplitst: de buzz/relay-datalaag → `chat/buzzcli.py`;
      server.py houdt routing + statische serving + main. Beide ≤ 200 regels.
- [x] 1.2 `chat/index.html`: inline `<style>` → `app.css`, inline `<script>` →
      `app.js` + `app-ui.js` (classic scripts, gedeelde global scope). index.html
      is nu een dunne shell. Server serveert de nieuwe assets; sw.js cachet ze.
- [x] 1.3 Gedrag behouden: de code-verplaatsing is verbatim (sed), maar omdat de
      app-logica/styling nu losse assets zijn i.p.v. inline in index.html, krijgen
      `app.css`/`app.js`/`app-ui.js` in sw.js dezelfde **netwerk-eerst**-behandeling
      als de pagina (anders zou een herlaad stale app-code tonen — regressie op
      add-pwa-fresh-reload). Import + JS-syntax geverifieerd; live-smoke op de VM.
- [x] 1.4 Nieuwe bronbestanden krijgen een SPDX-header (EUPL-1.2); README bijgewerkt.
