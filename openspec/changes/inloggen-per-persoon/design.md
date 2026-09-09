# Design — inloggen-per-persoon

## De keuze die alles bepaalt: welk credential

Ik heb eerder passkeys of OIDC aanbevolen. Bij het uitschrijven bleek een
wachtwoord met `hashlib.scrypt` de betere eerste stap, en dat verdient uitleg
omdat het tegen mijn eigen advies in gaat.

**Passkeys (WebAuthn) — het beste credential, niet de eerste stap.**
Phishing-bestendig, geen wachtwoord om te lekken, en op een telefoon prettiger
dan typen. Maar de serverkant moet CBOR/COSE ontleden en handtekeningen
verifiëren. Dat is óf een cryptobibliotheek in een backend die bewust
dependency-loos is (`push.py` zegt dat met zoveel woorden), óf zelf crypto
schrijven — precies de slimme valkuil waar dit project tegen waarschuwt. Een
half-goede WebAuthn-implementatie is slechter dan een goed wachtwoord. Passkeys
komen er als tweede credential op dezelfde sessielaag; die laag is er dan al.

**OIDC — de tweede stap, niet de eerste.** Geen wachtwoordopslag, en
offboarding gebeurt waar het hoort: bij de identiteitsvoorziening van de klant.
Technisch haalbaar zonder crypto-dependency, want een vertrouwelijke client die
de tokens rechtstreeks over TLS bij het token-endpoint ophaalt hoeft de
ID-token-handtekening niet te verifiëren en kan `userinfo` gebruiken. Maar elke
installatie moet dan éérst een client registreren bij een IdP voordat er ook
maar iemand kan inloggen. Voor het team met Entra of Authentik is dat tien
minuten; voor de solo-dev die dit "even installeert" is het een muur. Een MVP
die niemand doorkomt is geen MVP.

**Magic links per e-mail — afgewezen.** Dan hangt inloggen aan SMTP bij elke
installatie, en wordt e-mailbezorging een authenticatie-afhankelijkheid.

**Het gedeelde token houden — afgewezen.** Het is geen persoon, het is niet per
persoon in te trekken, en het staat op elk apparaat dat het ooit kreeg. Het is
precies wat we achterlaten.

**Basic auth in de reverse proxy — afgewezen.** Verplaatst authenticatie naar
een onderdeel dat wij niet meeleveren, en levert geen identiteit op in het
audit-spoor: de app weet dan nog steeds niet wie er schreef.

**Dus: wachtwoord (scrypt) + optioneel TOTP, allebei stdlib.** Saai, te lezen,
en het werkt op elk apparaat zonder dat de klant iets hoeft te regelen. `scrypt`
zit sinds 3.6 in `hashlib`; TOTP is RFC 6238 en met `hmac` een handvol regels
die je in één blik kunt nakijken. De parameters van elke hash worden bij de hash
opgeslagen, zodat ze later omhoog kunnen zonder iedereen uit te sluiten.

## Sessies

Ondoorzichtige tokens van 256 bit, in een cookie met `HttpOnly`, `SameSite=Lax`
en `Secure` (behalve op http://localhost, anders kun je lokaal niet ontwikkelen).
De sessies staan aan de serverkant, want:

- ze moeten per stuk intrekbaar zijn ("overal uitloggen") — dat kan een
  zelfdragend, ondertekend cookie niet;
- een ondertekend cookie verplaatst het probleem naar sleutelbeheer voor de
  ondertekening, en dat is niet minder werk.

Vervaltijd is een instelling met een saaie standaard (30 dagen, verlengd bij
gebruik). Een PWA die je één keer per week opent hoort niet elke keer opnieuw te
vragen; een gestolen sessie hoort niet eeuwig te leven.

## Waarom lezen óók achter de deur gaat

Het is de grootste gedragsverandering en het is niet onderhandelbaar: kanaalnamen,
berichten, agent-verkeer en repo-context staan in de leesroutes. Vandaag zijn ze
open omdat het tailnet ze afschermt. Bij een installatie zonder tailnet is
"lezen is open" hetzelfde als "alles is openbaar".

## CSRF

`SameSite=Lax` dekt het gewone geval, maar niet alles (een top-level POST
navigatie hoort er niet bij, maar de marge is te klein om op te leunen). Elk
statuswijzigend verzoek draagt daarom een sessiegebonden token, dat de app uit
zijn eigen sessie-antwoord haalt. Geen dubbel-cookie-truc: dat is moeilijker uit
te leggen dan het waard is.

## Opslag

Eén SQLite-bestand (stdlib, atomair, geen JSON die je bij elke schrijf helemaal
herschrijft) op 0600, in `/var/lib/boomhuis` naast de push-registraties — dus
buiten de checkout, zodat een redeploy geen accounts wist. Dat is dezelfde les
als bij `PUSH_SUBS_PATH`.

## Geen gebruikersopsomming, en een rem

Onbekende gebruiker en verkeerd wachtwoord geven hetzelfde antwoord en dezelfde
vertraging. Pogingen worden begrensd per account én per bron, met oplopende
wachttijd. Een self-hosted installatie op een LAN heeft geen WAF voor zich staan;
de rem hoort in de app.

## Wat de sessie NIET bepaalt

Wie je bent, niet welk sleutelpaar er onder je berichten hangt. Vandaag schrijft
`actions.py` met Marks buzz-sleutel; in een team moet elke persoon een eigen
relay-identiteit krijgen. Dat is `identity-registry`, en het is bewust een
aparte change: het raakt de sleutelopslag en de audit-keten, en dat wil je niet
in dezelfde stap als inloggen.
