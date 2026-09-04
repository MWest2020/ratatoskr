# Ontwerp — schrijf-token op de comms-API

## De vraag achter de keuze

Het dreigingsmodel is niet "iemand van het internet" (die komt er niet in) maar
**"iets op het tailnet dat niet Mark is"**. Elke oplossing moet dus iets eisen
dat een willekeurige tailnet-node níet heeft. Dat is de enige maatstaf waarop de
alternatieven hieronder verschillen.

## Gekozen: gedeeld token per apparaat, alleen op de schrijfpaden

`BOOMHUIS_APP_TOKEN` in `chat.env`, `X-App-Token` op `/api/send` en
`/api/channels/create|delete`, vergelijking met `hmac.compare_digest`, token
nooit in een log of foutmelding. De PWA vraagt het één keer en bewaart het in
`localStorage` van dat apparaat.

Saai, één env-var, geen nieuwe afhankelijkheid, en het faalt de goede kant op:
zonder token geen schrijfactie. Het past op het bestaande patroon (`BIND_HOST`
is ook config, geen code).

## Verworpen alternatieven

### 1. Token dat de server zelf in de pagina zet

Nul frictie: geen prompt, de PWA weet 'm gewoon. **Verworpen omdat het niets
oplost.** Wie de pagina kan ophalen, kan het token lezen — en precies dát kan
elke tailnet-node. Het zou een control zijn die exact tegen de aanvaller die we
modelleren geen drempel opwerpt.

### 2. Nostr-ondertekening per identiteit in de browser

Het inhoudelijk juiste antwoord, en het past op het kernprincipe van de
identity-registry: *identiteit = sleutelpaar, geen accountnaam*. De browser
tekent, de server verifieert tegen `identities.yml`, en berichten zijn echt
toerekenbaar in plaats van allemaal "mark".

**Verworpen voor nu, niet voor altijd.** Het betekent sleutelmateriaal in een
browser op een telefoon — voor een oppervlak dat al tailnet-only is, ruilen we
dan een klein risico in voor een groter. En het raakt de serverkant van de
identiteit (`buzzcli` tekent nu server-side als `mark`), dus het is een
herontwerp van de schrijfkant, geen toevoeging. Dit is het juiste vervolg zodra
boomhuis meer dan één mens bedient; dan vervalt dit token.

### 3. Tailscale Serve-identiteitsheaders (`Tailscale-User-Login`)

In principe beter dan een gedeeld geheim: echte identiteit per node, niets te
beheren, en een gedeelde of vreemde node valt buiten de allowlist. **Niet
gekozen omdat we het niet konden vaststellen zonder aan de serve-configuratie te
zitten**, en de repo-invariant zegt: *een agent wijzigt nooit de
relay-configuratie*. Het blijft de aantrekkelijkste vervanging van dit token —
als Mark ooit `tailscale serve` aanpast, is de check één `if` en verdwijnt het
gedeelde geheim. Genoteerd, niet stilzwijgend genegeerd.

### 4. Ook de leeskant achter het token

Consequenter, maar het maakt de PWA onbruikbaar vóór het token is ingevoerd
(je ziet niets, dus ook niet wáár je het moet invoeren) en het beschermt niets
extra's: meelezen op het tailnet is geen impersonatie, en de leeskant hangt al
achter tailnet + `tailscale serve`. Schrijven is het gedrag dat zich als Mark
voordoet; daar zit de grens.

## Wat dit expliciet níet is

Geen bescherming tegen Mark zelf, geen rate-limiting, en geen vervanging van de
netwerklaag: het token is de tweede laag, niet de eerste. Zodra `chat.env` van
de VM lekt, lekt het token mee — dat is aanvaard, want wie `chat.env` kan lezen,
staat al op de VM.
