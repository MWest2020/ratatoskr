#!/usr/bin/env bash
# Build the Android app (TWA) from twa-manifest.json and sign it.
#
# The app IS the PWA: Chrome renders it fullscreen. A new version of the chat is
# therefore in it immediately — you only run this script when the icon, the name,
# the start URL or the host changes.
#
#   bash android/build.sh             # -> android/ratatoskr-<version>.apk
#
# Needs once: JDK 17, the Android SDK (build-tools 36.1.0 + platform 36) and
# `npm i -g @bubblewrap/cli`. See docs/how-to/android-app.md.
#
# The signing key comes from SOPS and is NEVER a file in the repo.
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
# twa-manifest.json names ./ratatoskr.keystore — bubblewrap looks for it next to
# the project. A symlink, so the real file stays in the temporary directory and
# is removed with it.
ln -sf "$KS" "$HERE/ratatoskr.keystore"
trap 'rm -rf "$KSDIR"; rm -f "$HERE/ratatoskr.keystore"' EXIT

# Bubblewrap has TWO version fields: `appVersion` becomes the versionName in
# build.gradle, `appVersionName` is in the manifest. If they diverge, the APK
# says something other than the file — measured: an APK with versionName "Y"
# while the manifest said 0.2.0. Enforced hard here.
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
# Start clean. The generated Android project is derived from twa-manifest.json;
# leave it in place and build.gradle holds on to the previous build's version —
# measured: an APK with versionName "Y" while the manifest said 0.2.0. Throwing
# it away makes the build reproducible from one source.
rm -rf app build .gradle gradle gradlew gradlew.bat build.gradle settings.gradle \
       gradle.properties local.properties manifest-checksum.txt \
       app-release-unsigned-aligned.apk app-release-signed.apk
# `update` first: that generates the Android project from twa-manifest.json and
# writes the checksum. Without that step `build` asks interactively whether it may
# update the project, and then once more for a version name — a pipe does not
# answer that reliably (the prompt reads after what you push into it). Hence: no
# questions at all, stdin closed.
export BUBBLEWRAP_KEYSTORE_PASSWORD="$PW" BUBBLEWRAP_KEY_PASSWORD="$PW"
bubblewrap update --skipVersionUpgrade </dev/null >/dev/null 2>&1

# Bubblewrap signs too, and that fails on its own password handling. No matter:
# we only want the built, aligned APK and sign it explicitly with apksigner
# afterwards. One step less magic.
bubblewrap build --skipPwaValidation --skipVersionUpgrade </dev/null >/dev/null 2>&1 || true

test -f app-release-unsigned-aligned.apk || {
  echo "bubblewrap produced no apk — run it by hand to see the output" >&2; exit 1; }

"$BT/apksigner" sign --ks "$KS" --ks-key-alias ratatoskr \
  --ks-pass "pass:$PW" --key-pass "pass:$PW" \
  --out "ratatoskr-$VERSION.apk" app-release-unsigned-aligned.apk

echo "--- fingerprint (belongs in chat/well-known/assetlinks.json) ---"
"$BT/apksigner" verify --print-certs "ratatoskr-$VERSION.apk" \
  | grep -i "SHA-256 digest" | head -1
echo "done: $HERE/ratatoskr-$VERSION.apk"
