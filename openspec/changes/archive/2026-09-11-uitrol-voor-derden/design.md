# Design — uitrol-voor-derden

## Wat "installeerbaar" hier betekent

Niet: een installer. Wel: iemand met een machine, docker en dit compose-bestand
heeft binnen tien minuten een draaiend boomhuis, zonder iets van ons te weten.
Alles wat daarvoor uit iemands hoofd of uit een sessie met mij moet komen, is
een ontwerpfout.

De maat is dus concreet: een schone VM, `docker compose up -d`, `adminctl
eigenaar <naam>`, inloggen. Als daar een stap tussen zit die in geen enkel
bestand staat, is de change niet af.

## Waarom de chat een image wordt, en niet een systemd-unit met een checkout

De unit die er nu staat draait uit `/opt/buzz-build/chat` — een map die met
`scp` gevuld is en die daarnaast een Rust-buildboom en een APK bevat. Dat werkt
prima voor één machine met één beheerder die weet wat hij deed. Het faalt op
drie dingen zodra iemand anders het draait:

- **Versie.** Er is geen manier om te zeggen welke boomhuis er draait, dus ook
  niet om te zeggen of een bug al gerepareerd is.
- **Herhaalbaarheid.** "Kopieer deze bestanden" is geen uitrol; de volgende
  keer staat er iets anders.
- **Afhankelijkheden.** Nu is dat toevallig alleen python3. Dat blijft niet zo,
  en dan is de machine van de klant het probleem geworden.

Een image met een gepinde tag lost alle drie op, en past bij hoe de relay al
uitgerold wordt (`BUZZ_IMAGE` is al gepind). Prijs: bouwen en publiceren wordt
een stap in CI, en ontwikkelen op de VM ("even een bestand aanpassen") kan niet
meer. Dat laatste is winst vermomd als verlies.

## Blootstelling: standaard dicht, keuze expliciet

De huidige spec zegt "uitsluitend via het tailnet". Dat is een invariant die
alleen klopt in Marks huis. Wat ervoor in de plaats komt is geen "en nu open",
maar: **de standaard bindt op loopback, en de beheerder kiest**. Drie
gedocumenteerde vormen:

1. **Reverse proxy met TLS** (nginx, Caddy, Traefik) — het gewone geval voor
   een team. Wij termineren geen TLS; dat doet de proxy die er al staat.
2. **VPN of tailnet** — wat Mark doet. Dan is de proxy die tunnel.
3. **Bewust op het LAN** — mag, maar moet je aanzetten, en de documentatie zegt
   erbij wat je dan opgeeft.

De reden dat dit nu kán, is `inloggen-per-persoon`: elke aanroep hoort bij een
persoon. De netwerklaag was de enige control; nu is het de buitenste van twee.

## Het gat dat we onderweg tegenkwamen

De relay publiceert vandaag `"${BUZZ_HTTP_PORT:-3000}:3000"` zonder bind-adres,
dus `0.0.0.0:3000` — gemeten met `ss -ltnp` op de VM. Elke machine op het LAN
kan daar een TCP-verbinding opzetten. Dat is niet ernstig (de relay is closed,
een vreemde sleutel komt er op Nostr-niveau niet doorheen) maar het is wél iets
anders dan de spec belooft. Poorten krijgen daarom een expliciet bind-adres,
met `127.0.0.1` als standaard. Dat is precies het soort verschil tussen belofte
en werkelijkheid dat je alleen vindt door te kijken, en dat een derde partij
nooit zelf zou controleren.

## Staat: volumes, niet hostpaden

`auth.db` en `push_subs.json` staan nu in `/var/lib/boomhuis` op de host, buiten
de checkout — dat was destijds de goede keuze, want een redeploy wiste anders de
push-registraties. In een compose-stack is een named volume dezelfde gedachte,
maar dan zichtbaar in het bestand dat je uitrolt in plaats van in de
herinnering van wie het opzette.

## Verworpen: één image voor alles

Relay, database, opslag en chat in één container zou het installeren nóg
eenvoudiger maken. Afgewezen: de relay is upstream-software van iemand anders
met een eigen releaseritme, en die in ons image bakken betekent dat wij zijn
upgrades gaan dragen. De compose-stack houdt die grens waar hij hoort.

## Verworpen: TLS in de stack

Een Caddy meeleveren die zelf certificaten haalt, is verleidelijk en werkt goed
in demo's. In een echt netwerk botst dat met de proxy die er al staat, met
poort 80/443 die vaak al bezet is, en met certificaatbeheer dat een team meestal
centraal doet. Wij documenteren wat we verwachten en laten het aan de beheerder.
