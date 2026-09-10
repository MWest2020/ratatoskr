---
status: draft
last_reviewed: 2026-09-10
---

# Inloggen, uitnodigen, en wat te doen als je jezelf buitensluit

Sinds `inloggen-per-persoon` hoort elke aanroep bij een persoon — ook lezen.
Het gedeelde schrijf-token is weg.

## De eerste keer — vanaf de host, zonder browser

De kortste weg, en de weg die het altijd doet: op de machine waar de
installatie draait.

    cd /opt/buzz-build/chat
    sudo python3 adminctl.py eigenaar <jouw-naam>

Hij vraagt je wachtwoord twee keer, zichtbaar noch in je shell-geschiedenis.
Daarna log je in op `/login`.

Meer opdrachten: `personen` (wie er zijn), `uitnodiging` (link voor iemand
anders), `wachtwoord <naam>` (nieuw wachtwoord, trekt alle sessies van die
persoon in), `verwijder <naam>`.

## De eerste keer — via de browser

Bij een installatie zonder accounts drukt de server bij het starten een
eenmalige link af:

    journalctl -u boomhuis-chat | grep setup=

Open die link, kies een naam en een wachtwoord van minstens twaalf tekens. Je
bent dan de eigenaar. De link werkt daarna niet meer.

Draaide er al een boomhuis met `BOOMHUIS_APP_TOKEN`? Dan werkt dat oude token
eenmalig ook: open `/login`, de pagina ziet dat er nog niemand is en vraagt om
het token. Zodra er één account bestaat vervalt die weg — daarna is het token
nergens meer goed voor en kan het uit `chat.env`.

## Iemand erbij

Als eigenaar: open de kanalen-lade, *Iemand uitnodigen*. Je krijgt een link op
je klembord die één keer werkt en na een week verloopt. Zelf-registratie
bestaat niet: één installatie is één team.

Een uitnodiging die je niet meer wilt trek je in met alle andere:

    curl -X POST -H "X-CSRF-Token: <token>" --cookie "bh_session=<sessie>" \
         https://<boomhuis>/api/uitnodiging/intrekken

## Tweede factor

Optioneel, per persoon: `POST /api/totp/start` geeft een geheim en een
`otpauth:`-URI voor je authenticator, `POST /api/totp/aan` met een kloppende
code zet hem aan. Hij gaat pas aan ná die code — anders sluit een verkeerd
overgetypt geheim je uit je eigen account. Uitzetten kan met
`POST /api/totp/uit`.

## Jezelf buitengesloten

In de app zit nog geen wachtwoord-vergeten; vanaf de host wel:

    cd /opt/buzz-build/chat
    sudo python3 adminctl.py wachtwoord <naam>

Dat zet een nieuw wachtwoord en trekt alle sessies van die persoon in — wie het
oude had, is eruit.

Helemaal opnieuw beginnen kan ook: `verwijder <naam>` voor iedereen, daarna
`eigenaar <naam>`. Kanalen en berichten staan op de relay en raak je daarmee
niet kwijt; accounts zijn het enige dat in `auth.db` staat.
