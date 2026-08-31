---
status: actief
last_reviewed: 2026-08-31
---

# De Boomhuis-app op je telefoon zetten (PWA)

De webchat is een installeerbare PWA: geen app store, gewoon de site "toevoegen
aan je beginscherm". Daarna start hij als losse app, zonder browserbalk.

## Vereisten

- Je telefoon is een **node in het tailnet**: Tailscale-app geïnstalleerd,
  ingelogd en verbonden. Buiten het tailnet is de app niet bereikbaar — dat is
  opzet, er is geen publieke voordeur. Toegang loopt uitsluitend via het tailnet;
  de app zelf heeft geen login. Ze post namens de identiteit `mark`, die
  server-side is geconfigureerd (er staat geen sleutel in je browser).

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
4. Bevestig. Het Boomhuis-icoon staat nu tussen je apps.

## iOS (Safari)

Op iOS kan dit **alleen in Safari** — Chrome of Firefox hebben de optie niet.

1. Open de URL in **Safari**.
2. Tik op **Deel** (het vierkantje met de pijl omhoog).
3. Scroll in het menu naar **Zet op beginscherm**.
4. Geef eventueel een naam en tik **Voeg toe**.

## Daarna

De app start als losse app. Ze praat met dezelfde backend als op desktop en post
namens `mark`; er staat geen sleutel in je browser, dus kanalen en berichten zijn
overal hetzelfde. Verwijderen doe je als bij elke app — icoon ingedrukt houden →
verwijderen.
