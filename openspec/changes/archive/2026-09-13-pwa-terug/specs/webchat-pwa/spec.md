# webchat-pwa

## REMOVED Requirements

### Requirement: De installatie levert een Android-app die de PWA draait

**Reden:** een Trusted Web Activity verifieert zijn herkomst bij elke start via
`/.well-known/assetlinks.json`. Op een origin die alleen via een tunnel
bereikbaar is, faalt die controle zodra de tunnel nog niet op is, en dan start de
app als browservenster mét adresbalk. Gemeten op Marks toestel, 2026-09-12.

De geïnstalleerde PWA (`display: standalone`) heeft geen browser-interface en
doet geen herkomstcontrole. Die is voor deze installatie dus strikt beter, en de
app leverde alleen een mooier icoon op.

Wat blijft: de ondertekensleutel in SOPS (`secrets/android-signing.yaml`). Een
volgende echte app hoort dezelfde identiteit te dragen, en die identiteit *is*
die sleutel. Het bouwspul onder `android/` gaat wel weg.
