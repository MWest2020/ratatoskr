#!/usr/bin/env bash
# Bouw de Android-app (TWA) uit twa-manifest.json en onderteken 'm.
#
# De app IS de PWA: Chrome rendert 'm fullscreen. Een nieuwe versie van de chat
# zit er dus meteen in — dit script draai je alleen als het icoon, de naam, de
# start-URL of de host verandert.
#
#   bash android/build.sh             # -> android/ratatoskr-<versie>.apk
#
# Vereist eenmalig: JDK 17, Android SDK (build-tools 36.1.0 + platform 36) en
# `npm i -g @bubblewrap/cli`. Zie docs/how-to/android-app.md.
#
# De ondertekensleutel komt uit SOPS en staat NOOIT in de repo als bestand.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/android-sdk}"
BT="${BUILD_TOOLS:-$ANDROID_HOME/build-tools/36.1.0}"

KSDIR="$(mktemp -d)"
trap 'rm -rf "$KSDIR"' EXIT
python3 "$HERE/extract-key.py" "$KSDIR" >/dev/null
KS="$KSDIR/ratatoskr.keystore"
PW="$(cat "$KSDIR/password.txt")"
# twa-manifest.json noemt ./ratatoskr.keystore — bubblewrap zoekt 'm naast het
# project. Een link, zodat het echte bestand in de tijdelijke map blijft en bij
# het opruimen meegaat.
ln -sf "$KS" "$HERE/ratatoskr.keystore"
trap 'rm -rf "$KSDIR"; rm -f "$HERE/ratatoskr.keystore"' EXIT

# Bubblewrap kent TWEE versievelden: `appVersion` wordt de versionName in
# build.gradle, `appVersionName` staat in het manifest. Lopen ze uiteen, dan
# zegt de APK iets anders dan het bestand — gemeten: een APK met versionName
# "Y" terwijl het manifest 0.2.0 zei. Hier hard afdwingen.
VERSION="$(python3 - "$HERE/twa-manifest.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
a, b = d.get("appVersion"), d.get("appVersionName")
if a != b:
    sys.exit("twa-manifest.json: appVersion (%r) != appVersionName (%r)" % (a, b))
print(b)
PY
)"

cd "$HERE"
# Schoon beginnen. Het gegenereerde Android-project is afgeleide van
# twa-manifest.json; laat je het staan, dan houdt build.gradle de versie van de
# vórige build vast — gemeten: een APK met versionName "Y" terwijl het manifest
# 0.2.0 zei. Weggooien maakt de build reproduceerbaar uit één bron.
rm -rf app build .gradle gradle gradlew gradlew.bat build.gradle settings.gradle \
       gradle.properties local.properties manifest-checksum.txt \
       app-release-unsigned-aligned.apk app-release-signed.apk
# Eerst `update`: dat genereert het Android-project uit twa-manifest.json én
# schrijft de checksum. Zonder die stap vraagt `build` interactief of hij het
# project mag bijwerken, en daarna nóg een keer om een versienaam — een pipe
# beantwoordt dat niet betrouwbaar (de prompt leest ná wat je erin duwt).
# Daarom: geen enkele vraag, stdin dicht.
export BUBBLEWRAP_KEYSTORE_PASSWORD="$PW" BUBBLEWRAP_KEY_PASSWORD="$PW"
bubblewrap update --skipVersionUpgrade </dev/null >/dev/null 2>&1

# Bubblewrap tekent zelf ook, en dat faalt op zijn eigen wachtwoord-afhandeling.
# Niet erg: we willen alleen de gebouwde, uitgelijnde APK en tekenen die daarna
# expliciet met apksigner. Eén stap minder magie.
bubblewrap build --skipPwaValidation --skipVersionUpgrade </dev/null >/dev/null 2>&1 || true

test -f app-release-unsigned-aligned.apk || {
  echo "bubblewrap leverde geen apk — draai 'm met de hand voor de uitvoer" >&2; exit 1; }

"$BT/apksigner" sign --ks "$KS" --ks-key-alias ratatoskr \
  --ks-pass "pass:$PW" --key-pass "pass:$PW" \
  --out "ratatoskr-$VERSION.apk" app-release-unsigned-aligned.apk

echo "--- vingerafdruk (hoort in chat/well-known/assetlinks.json) ---"
"$BT/apksigner" verify --print-certs "ratatoskr-$VERSION.apk" \
  | grep -i "SHA-256 digest" | head -1
echo "klaar: $HERE/ratatoskr-$VERSION.apk"
