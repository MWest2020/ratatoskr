# Design — herstel-na-koude-start

## Waarom niet gewoon een try/catch om `init()`

Dat maakt het stil falen alleen stiller: de app zou niet meer crashen, maar
nog steeds nooit opnieuw proberen. De kern is niet dat er een exception valt,
maar dat er na de eerste mislukking niets meer gebeurt. Vandaar de volgorde:
eerst de motor (timers, luisteraars), dan pas de eerste rit.

## Waarom de service worker ongemoeid blijft

Zijn cache-fallback lijkt de boosdoener — zonder hem zou de app gewoon niet
laden en zou je de fout meteen zien. Maar dat gedrag staat in de spec en is
gewenst: op een telefoon komt de tailnet-tunnel later op dan de app, en een
lege pagina is slechter dan een shell die op zijn gegevens wacht. De fout zit
in wat de app dóét met een shell zonder netwerk, niet in het serveren ervan.

## Verworpen: berichten cachen voor offline lezen

Zou de "laden…" ook wegnemen, maar zet een tweede waarheid naast de relay en
schendt de regel dat `/api/` nooit gecachet wordt (chat is realtime). Een
expliciete "geen verbinding"-melding is eerlijker dan oude berichten tonen
alsof ze vers zijn.

## Herhaalritme

Vast interval van 3 s, geen exponentiële backoff. De app draait op een
tailnet dat binnen seconden opkomt of helemaal niet; een backoff die naar
minuten kruipt zou juist het geval treffen waar dit voor bedoeld is. De poll
van 4 s die er al is bepaalt het ritme zodra de kanalen binnen zijn.
