# Change: inloggen-per-persoon

## Why

Boomhuis wordt een app die derden zelf installeren (self-hosted, één team per
installatie, klant brengt zijn eigen modeltoegang). Van de vier invarianten die
dat breekt — zie `docs/naar-een-product.md` — is dit de eerste, want zonder
authenticatie heeft de rest geen fundament.

Vandaag is er geen. Lezen in de comms-API is volledig open; `auth.py` bewaakt
alleen schrijven met één gedeeld token, en de docstring zegt zelf dat het
tailnet "de primaire control" is. Dat werkt voor één mens op zijn eigen
tailnet. Het werkt niet zodra er een tweede mens is: één token is geen persoon,
is niet per persoon in te trekken, en staat op elk apparaat dat het ooit kreeg.

Twee dingen maken dit kleiner dan het lijkt:

- **De API is mensenwerk.** Agents posten niet via HTTP maar met de `buzz`-CLI
  rechtstreeks op de relay (`orchestrator/ping.sh`). Er is dus geen
  machine-authenticatie nodig in deze change.
- **De netwerklaag verandert niet.** Na deze change blijft tailnet-only de
  standaard-uitrol; authenticatie is daar óók winst zodra er meer dan één mens
  is. Het netwerk opengooien is een aparte beslissing en een aparte change.

## What changes

- **Elke API-aanroep hoort bij een persoon.** Lezen én schrijven vereisen een
  sessie; zonder sessie is het antwoord 401. Dat is de grootste
  gedragsverandering: lezen was open.
- **Geen standaardwachtwoord.** Bij de eerste start zonder accounts drukt de
  server een eenmalige setup-link af; wie die opent wordt eigenaar.
- **Mensen komen erbij via een eenmalige, verlopende uitnodiging** die de
  eigenaar maakt.
- **Wachtwoord + optioneel TOTP**, allebei met de standaardbibliotheek:
  `hashlib.scrypt` voor de hash (parameters bij de hash opgeslagen, zodat ze
  later omhoog kunnen), en RFC 6238 met `hmac` voor de tweede factor.
- **Sessies** zijn ondoorzichtige tokens in een HttpOnly-cookie, met vervaltijd
  en per stuk intrekbaar ("overal uitloggen").
- **Het gedeelde `BOOMHUIS_APP_TOKEN` verdwijnt** als authenticatiemiddel. Bij
  een bestaande installatie mag het één keer dienen om de eigenaar aan te maken,
  daarna niet meer.

## Wat hier NIET in zit

- **Passkeys en OIDC.** Allebei betere credentials dan een wachtwoord, allebei
  een eigen change op dezelfde sessielaag. Waarom niet nu: zie `design.md`.
- **Rechten per persoon.** Eén installatie is één team; iedereen ziet alles.
- **Machine-identiteiten / service-tokens.** Niet nodig zolang agents de relay
  rechtstreeks gebruiken.
- **De koppeling persoon → relay-identiteit.** De sessie bepaalt wíe je bent;
  welk sleutelpaar daarbij hoort is werk voor `identity-registry`.
- **Het netwerkmodel.** `relay-deployment` houdt zijn tailnet-eis.

## Impact

- Nieuwe capability `auth`; nieuwe modules naast `server.py` (opslag, routes,
  wachtwoord/TOTP), elk onder de 200 regels uit `CLAUDE.md`.
- `webchat-pwa`: de twee apparaat-token-eisen vervallen en worden vervangen door
  inloggen; `app-auth.js` wordt herschreven.
- Een inlogpagina in de shell van de service worker, en in de statics-allowlist
  van `server.py` — die allowlist is twee keer eerder vergeten en gaf dan een
  404 op een nieuw bestand.
- Opslag: één SQLite-bestand (stdlib) op 0600 buiten de checkout, naast
  `push_subs.json` in `/var/lib/boomhuis`.
- Bestaande installatie: het opgeslagen apparaat-token in de PWA wordt waardeloos
  en de app stuurt je naar inloggen. Dat is de bedoelde eenmalige hobbel.
