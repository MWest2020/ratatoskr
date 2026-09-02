## Why

De Repos-lade (📦 Repos) had geen eigen CSS en geen sluitknop: eenmaal geopend
was er geen duidelijke weg terug naar de chat, en de navigatie repo-lijst → PR's
→ PR-detail voelde janky. Mark: "eenmaal op geklikt gaat slecht terug."

## What Changes

- **De Repos-lade wordt een echte modal**: eigen overlay + sheet (volledig scherm,
  slide-up van onder, scrollbaar) in `app.css`.
- **Sluitknop (✕)** in een kop-balk, die vanaf elk niveau terug naar de chat gaat.
- De bestaande **← level-back**-links (repo's / PR's) blijven voor navigatie
  binnen de lade. Geen wijziging aan de repo/PR-data of endpoints.
