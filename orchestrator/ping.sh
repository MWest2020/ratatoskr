#!/usr/bin/env bash
# Post een bericht als 'bouwer' naar #general — de ping-lus met Mark in de app.
# Bericht via arg of stdin. Geen secret in dit bestand: de nsec komt uit SOPS.
set -euo pipefail
MSG="${1:-$(cat)}"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GEN=$(python3 -c "import yaml;print(yaml.safe_load(open('$ROOT/channels.yml'))['channels']['general']['id'])")
# eigen npub als --mention: staat willekeurige @-woorden toe (presentation-only),
# net als de listener/chat-backend; anders weigert buzz onbekende @mentions.
NPUB=$(python3 -c "import yaml;print(yaml.safe_load(open('$ROOT/identities.yml'))['identities']['bouwer']['npub'])")
NSEC=$(sops -d "$ROOT/secrets/identities.yaml" \
  | python3 -c "import sys,yaml;print(yaml.safe_load(sys.stdin)['identities']['bouwer']['nsec'])")
BUZZ_PRIVATE_KEY="$NSEC" BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}" \
  ~/.local/bin/buzz messages send --channel "$GEN" --content - --mention "$NPUB" <<<"$MSG" >/dev/null
echo "[ping] verstuurd naar #general"
