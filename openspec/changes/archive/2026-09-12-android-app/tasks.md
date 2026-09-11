# Taken

## 1. Bouwen
- [x] 1.1 Bouwgereedschap (JDK + Android-SDK + bubblewrap) op agent-lxc
- [x] 1.2 `android/` : bubblewrap-project met onze manifest-URL, naam, icoon
- [x] 1.3 Keystore maken en SOPS+age-versleuteld in `secrets/`
- [x] 1.4 APK bouwen en ondertekenen; vingerafdruk uitlezen

## 2. Asset-links
- [x] 2.1 `/.well-known/assetlinks.json` serveren (open route, geen sessie)
- [x] 2.2 Meten dat de app zonder adresbalk start — bevestigd door Mark op zijn
      toestel (2026-09-11): "geen adresbalk, werkt"
      serverzijde is klaar (assetlinks open + vingerafdruk gelijk aan de APK)

## 3. Uitleveren
- [x] 3.1 De APK downloadbaar vanaf de eigen installatie
- [x] 3.2 Op Marks telefoon installeren en gebruiken — gedaan

## 4. Vastleggen
- [x] 4.1 `docs/how-to/android-app.md`: bouwen, bumpen, en wat je nooit weggooit
- [x] 4.2 Change archiveren
