## ADDED Requirements

### Requirement: Telefoon-push bij verdict en escalatie

Naast de post in `#runs`/`#escalatie` SHALL `buzz-notify.sh` bij een run-einde
(verdict) en bij een escalatie een Web Push naar de geregistreerde apparaten
afvuren, zodat Mark de melding ook op de telefoon krijgt met de app gesloten.
Dit SHALL opt-in zijn via `BUZZ_PUSH=1` en SHALL de bestaande best-effort-garantie
erven: een ontbrekende sender, lege uv-cache of onbereikbare push-service SHALL een
run nooit vertragen of laten falen (de aanroep is achtergrond + getimed, fouten
gaan naar `notify.log`). De push SHALL alleen metadata bevatten (verdict, change,
branch, reden) — nooit geheimen — conform de bestaande spiegel-eis.

#### Scenario: Verdict met push aan

- **WHEN** een run eindigt terwijl `BUZZ_PUSH=1` en er ten minste één apparaat is
  aangemeld
- **THEN** verschijnt het verdict zowel als bericht in `#runs` als als push-melding
  op het toestel, en blokkeert het versturen de afronding van de run niet

#### Scenario: Push-pad kapot, run ongemoeid

- **WHEN** de sender ontbreekt of de push-service onbereikbaar is bij een run-einde
- **THEN** rondt de run normaal af, staat de `#runs`-post er gewoon, en logt de
  orchestrator de gemiste push zonder de run te vertragen of te laten falen
