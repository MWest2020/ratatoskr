# Ontwerp: de Android-app

## Waarom een TWA en niet een eigen app

**Gekozen: Trusted Web Activity (Bubblewrap).** De app ís de PWA. Chrome rendert
'm fullscreen, deelt service worker, opslag, sessiecookie en pushmeldingen met de
browser, en er is geen regel app-code om te onderhouden. Een nieuwe versie van de
chat is er meteen in; de APK verandert alleen als het icoon, de naam of de
start-URL verandert.

**Verworpen: een WebView-wrapper.** Simpeler te bouwen, maar een WebView is geen
Chrome: eigen opslag (dus opnieuw inloggen), geen service worker die je deelt,
geen Web Push, en een render-engine die per fabrikant verschilt. Je koopt een
icoon en betaalt met alles eronder.

**Verworpen: Capacitor/Cordova.** Dezelfde WebView-bezwaren plus een
JavaScript-bruglaag die we nergens voor gebruiken.

**Verworpen: een native client.** Een tweede codebase voor precies dezelfde
schermen, in een project waar één persoon alles onderhoudt. Dat is de definitie
van technische schuld.

## Asset-links: waarom het bestand er moet staan

Een TWA is "trusted" doordat Chrome op het toestel
`https://<origin>/.well-known/assetlinks.json` ophaalt en daar de SHA-256 van de
ondertekensleutel van de geïnstalleerde app in terugvindt. Klopt dat niet, dan
start de app alsnog met een adresbalk — technisch een Custom Tab. Daarom is dat
bestand geen detail maar de helft van de functie.

Gevolg voor ons: de verificatie gebeurt **op het toestel**, dus de telefoon moet
de origin kunnen bereiken. Op het tailnet gaat dat goed zolang de telefoon
aangekoppeld is — wat toch al moet, anders is er geen chat. Een derde met een
publieke reverse proxy heeft er helemaal geen last van.

## De sleutel is het enige onvervangbare

**Gekozen: keystore SOPS+age in `secrets/`, zoals de nsecs.** Android bepaalt de
identiteit van een app aan de ondertekensleutel. Raak je 'm kwijt, dan is een
volgende build voor Android een *andere* app: gebruikers moeten de oude
verwijderen en de nieuwe installeren, en de asset-links moeten opnieuw.

**Verworpen: sleutel op de host, buiten git** (zoals de relay-`.env`). Dat past
bij secrets die per installatie verschillen; deze hoort bij de app, niet bij een
machine, en moet een herinstallatie van agent-lxc overleven.

**Verworpen: Play App Signing.** Google bewaart de sleutel dan voor je. Prima
voor een Play-app, maar dit ding hoort juist zonder Google te kunnen.

## Uitleveren zonder winkel

**Gekozen: de APK staat op de eigen installatie**, te downloaden vanaf dezelfde
origin. Wie bij de chat kan, kan bij de app.

**Verworpen: Play Store.** Vergt een ontwikkelaarsaccount, een review, en een
publiek bereikbare privacy-verklaring — voor een app die alleen binnen iemands
eigen netwerk werkt. Later, als er derden zijn die dat willen.

**Verworpen: de APK in git.** Een binair bestand dat elke build verandert. Hij
komt naast de installatie te staan, niet erin.

## Wat dit NIET oplost

De app is de PWA. Geen tailnet is geen chat, ook in de app. Offline werkt precies
zover als de service worker reikt, geen meter verder. En de eerste keer moet de
gebruiker nog steeds inloggen — de app deelt de cookie met Chrome, dus daarna
niet meer.
