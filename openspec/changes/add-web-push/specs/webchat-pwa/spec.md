## ADDED Requirements

### Requirement: Telefoon-notificaties via Web Push

De geïnstalleerde PWA SHALL de gebruiker kunnen abonneren op Web Push, zodat
meldingen (bv. een review-verdict) ook binnenkomen als de app gesloten is. De
VAPID-private-sleutel SHALL niet op de web-facing backend staan; het versturen
gebeurt buiten de stdlib-backend.

#### Scenario: Aanmelden en een melding ontvangen

- **WHEN** de gebruiker meldingen aanzet (permissie geeft) en er wordt een push
  verstuurd
- **THEN** toont het apparaat een notificatie, ook als de app-tab/app gesloten is,
  en opent een tik erop de app
