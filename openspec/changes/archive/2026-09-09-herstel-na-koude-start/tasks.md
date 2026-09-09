# Tasks — herstel-na-koude-start

## 1. Reproduceren

- [x] 1.1 `chat/e2e/offline-boot.js` reproduceerde de storing eerst: 4 van de
      6 checks rood, met het scherm op "laden…" en een lege kanaallijst, óók
      nadat de API weer antwoordde. Na de fix 6/6.

## 2. Herstel

- [x] 2.1 `init()` zet poll-timer en luisteraars vóór de eerste netwerkaanroep.
- [x] 2.2 `loadChannels()` faalt zacht en wordt herhaald tot het lukt.
- [x] 2.3 `refresh()` toont een verbindingsfout in plaats van stil te stoppen,
      en overschrijft geen al gerenderde berichten.
- [x] 2.4 `online` en `visibilitychange` proberen het meteen opnieuw.

## 3. Nameten

- [x] 3.1 `offline-boot.js` groen tegen de echte VM.
- [x] 3.2 De bestaande e2e-suite blijft groen: api.sh 36/36, ui.js 20/20,
      xss.js alles, deeplink.js 5/5. `verify.sh` groen (85 unittests).
- [x] 3.3 `app.js` + `app-ui.js` uitgerold naar `/opt/buzz-build/chat`
      (md5 gelijk aan de repo) en met offline-boot.js in een echte browser
      tegen de VM nagemeten: 6/6.
