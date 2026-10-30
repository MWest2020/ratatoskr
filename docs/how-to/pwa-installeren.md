---
status: actief
last_reviewed: 2026-09-13
---

# De Ratatoskr-app op je telefoon zetten (PWA)

De webchat is een installeerbare PWA: geen app store, gewoon de site "toevoegen
aan je beginscherm". Daarna start hij als losse app, zonder browserbalk.

## Vereisten

- Je telefoon is een **node in het tailnet**: Tailscale-app geïnstalleerd,
  ingelogd en verbonden. Buiten het tailnet is de app niet bereikbaar — dat is
  opzet, er is geen publieke voordeur. Toegang loopt uitsluitend via het tailnet.
  Ze post namens de identiteit `mark`, die server-side is geconfigureerd (er
  staat geen sleutel in je browser).
- **Een schrijf-token**, als de deployment er een instelt. Lezen kan zonder;
  zodra je iets probeert te versturen, vraagt de app het token één keer en
  onthoudt het op dít apparaat. Zie [Schrijf-token](#schrijf-token).

## De URL

```
https://boomhuis-relay.tail8f7877.ts.net/
```

Werkt de URL niet? Controleer eerst of Tailscale actief is (schakelaar aan in de
app). Daarna, op de relay-VM: draait de chat-backend (`systemctl status
boomhuis-chat`) en staat de HTTPS-voorkant aan (`tailscale serve status`)? Pas
als de relay zelf stuk is, is [relay-herstel](relay-herstel.md) aan de orde.

## Android (Chrome)

1. Open de URL in **Chrome**.
2. Chrome toont meestal een **Installeren**-knop in de adresbalk of een balkje
   onderaan. Tik die aan.
3. Zie je hem niet: menu **⋮** → **App installeren** (of **Toevoegen aan
   startscherm**).
4. Bevestig. Het Ratatoskr-icoon staat nu tussen je apps.

## iOS (Safari)

Op iOS kan dit **alleen in Safari** — Chrome of Firefox hebben de optie niet.

1. Open de URL in **Safari**.
2. Tik op **Deel** (het vierkantje met de pijl omhoog).
3. Scroll in het menu naar **Zet op beginscherm**.
4. Geef eventueel een naam en tik **Voeg toe**.

## Meldingen aanzetten (Web Push)

Wil je verdicts en escalaties als melding op je telefoon (ook met de app dicht)?

1. Open de geïnstalleerde app en tik rechtsboven op de **🔔**-knop.
2. Sta meldingen toe. Klaar.

### Waar je wél en niet een melding van krijgt

| wel | niet |
| --- | --- |
| een antwoord van een agent | je eigen berichten |
| een bericht van iemand anders | de `⋯`-voortgangsregels |
| een run-verdict en een escalatie | alles in `#statistics` |

Per kanaal gaat er hooguit één melding per 45 seconden uit. Komt er binnen dat
venster nog iets, dan wordt dat **uitgesteld, niet overgeslagen**: zodra de 45
seconden om zijn stuurt de listener het alsnog, met achter de tekst hoeveel
berichten er nog meer waren (`(+2 eerder)`). Tot 18-09-2026 verdween zo'n bericht
en dook de teller pas op achter het vólgende bericht in dat kanaal — in de meting
vier dagen later.

Zie je geen 🔔? Dan ondersteunt deze context geen Web Push. Belangrijk voor iOS:
**push werkt daar alleen in de op-het-beginscherm geïnstalleerde app** (iOS 16.4+),
niet in een gewone Safari-tab — installeer de app dus eerst (stap hierboven). Op
Android/desktop-Chrome werkt de knop ook in een tab.

## Schrijf-token

Het tailnet houdt vreemden buiten, maar wie er al op zit kon tot nu toe zonder
meer berichten sturen — en die komen aan als `mark`. Daarom kan de deployment een
schrijf-token eisen (`BOOMHUIS_APP_TOKEN` in `chat.env` op de relay-VM).

- **Lezen** werkt zonder token: kanalen en berichten zie je gewoon.
- **Schrijven** (bericht sturen, kanaal maken of verwijderen, een agent
  toevoegen, meldingen aanzetten) vraagt eenmalig om het token. Daarna staat het
  in de opslag van dit apparaat en merk je er niets meer van.
- Nieuw apparaat = één keer opnieuw invoeren. Browsergegevens gewist = ook
  opnieuw.
- Krijg je onverwacht de vraag om een token? Dan is het op de server gewijzigd,
  of je zit op een ander apparaat dan je denkt.

Het token staat **niet** in de pagina en wordt er nooit door de server in gezet:
wie de pagina kan ophalen, zou het anders kunnen lezen — en dat is precies de
node waartegen het bedoeld is.

## Daarna

De app start als losse app. Ze praat met dezelfde backend als op desktop en post
namens `mark`; er staat geen sleutel in je browser, dus kanalen en berichten zijn
overal hetzelfde. Het schrijf-token is wel per apparaat. Verwijderen doe je als bij elke app — icoon ingedrukt houden →
verwijderen.
