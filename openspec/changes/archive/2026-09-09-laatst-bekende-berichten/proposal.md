# Change: laatst-bekende-berichten

## Why

Meldingen komen áltijd aan; de app kan alleen op het tailnet laden. Dat is
geen toeval maar een asymmetrie in het ontwerp: Web Push loopt over
`fcm.googleapis.com` — publiek internet, los van Tailscale — en de
comms-API staat achter het tailnet. Nagemeten in de push-subscriptions op
de VM.

Gevolg: je krijgt een melding, tikt erop (die linkt sinds #51 netjes naar
het juiste kanaal), en landt in een app die niets kan tonen. Vandaag was
dat zes uur lang de werkelijkheid omdat Tailscale op het toestel uit
stond. De app zegt sinds vanmiddag eerlijk dát er geen verbinding is —
maar een leeg scherm blijft het antwoord.

Er is bijna altijd wél iets zinnigs te tonen: wat je de vorige keer al
gelezen had. Dat is geen tweede waarheid zolang het zichtbaar gedateerd
is en er niets mee geschreven kan worden.

## What changes

- De app bewaart per kanaal een **momentopname** van de laatst opgehaalde
  berichten (met tijdstip) in `localStorage`.
- Kan hij niets ophalen, dan toont hij die momentopname mét een balk
  *"offline — laatst bijgewerkt om HH:MM"* in plaats van een leeg scherm.
  De knoppen *opnieuw proberen* en *app verversen* blijven eronder staan.
- Zodra er wél verbinding is, verdwijnt de balk en vervangt verse data de
  momentopname. Verzenden verandert niet: dat faalt zichtbaar zoals nu.

## Wat hier NIET in zit

- **Geen wachtrij voor verzenden.** Een bericht dat later alsnog vertrekt
  komt buiten volgorde aan, kan dubbel landen en botst met "git is de
  waarheid, buzz is de spiegel". Weigeren met een leesbare melding is
  eerlijker dan stiekem uitstellen.
- **Geen `/api/`-caching in de service worker.** Die regel blijft staan:
  de worker weet niet of iets vers is, de app wel. De momentopname is van
  de app, met een tijdstip erbij.
- Geen offline zoeken, geen offline kanaalbeheer.

## Impact

- Nieuw bestandje `chat/app-cache.js` (opslag + de gedateerde weergave),
  plus de haakjes in `app.js` en `app-verbinding.js`.
- `index.html`, `sw.js` (shell + verse assets + cacheversie) en de
  statics-allowlist in `server.py` — die laatste is makkelijk te vergeten
  en geeft anders een 404 op het nieuwe bestand.
- `offline-boot.js` krijgt er een geval bij: eerst online laden, dan de
  API blokkeren en herladen; de berichten horen er nog te staan, gedateerd.
