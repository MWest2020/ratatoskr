#!/usr/bin/env bash
# Post een bericht naar #general — de ping-lus met Mark in de app.
# Identiteit via env IDENT (default 'bouwer', zodat bestaande aanroepen blijven
# werken); bericht via arg of stdin. Geen secret in dit bestand: de nsec komt
# uit SOPS. Zet IDENT op je eigen sessie-identiteit zodat berichten aan de echte
# afzender toe te schrijven zijn (identiteit = sleutelpaar, geen naam-prefix).
#   IDENT=hubby ~/boomhuis/orchestrator/ping.sh 'mijlpaal: ...'
set -euo pipefail
IDENT="${IDENT:-bouwer}"
MSG="${1:-$(cat)}"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

GEN=$(python3 -c "import yaml;print(yaml.safe_load(open('$ROOT/channels.yml'))['channels']['general']['id'])")
NPUB=$(python3 -c "
import yaml,sys
d=yaml.safe_load(open('$ROOT/identities.yml'))['identities']
if '$IDENT' not in d: sys.stderr.write(\"onbekende IDENT '$IDENT' (niet in identities.yml)\n\"); sys.exit(3)
rol=d['$IDENT'].get('rol')
# Alleen sessie- of chat-agent-identiteiten mogen via ping.sh posten. Zo kan
# niemand zich als de mens ('mark', rol mens) of een andere klasse voordoen.
if rol not in ('sessie','chat-agent'):
    sys.stderr.write(\"IDENT '$IDENT' (rol=%s) mag niet via ping.sh posten — alleen 'sessie'/'chat-agent'\n\"%rol); sys.exit(4)
print(d['$IDENT']['npub'])")
NSEC=$(sops -d "$ROOT/secrets/identities.yaml" \
  | python3 -c "import sys,yaml;print(yaml.safe_load(sys.stdin)['identities']['$IDENT']['nsec'])")

# Relay via de community-host 192.168.178.60 (de relay is community-scoped op DEZE
# host; het tailnet-IP geeft "no community configured for this host"). Vanaf een
# tailnet-node werkt dit via de subnet-router die 192.168.178.0/24 adverteert;
# override met env BUZZ_RELAY_URL. Eigen npub als --mention: staat vrije @-woorden
# toe (presentation-only), anders weigert buzz onbekende @mentions.
BUZZ_PRIVATE_KEY="$NSEC" BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}" \
  ~/.local/bin/buzz messages send --channel "$GEN" --content - --mention "$NPUB" <<<"$MSG" >/dev/null
echo "[ping] verstuurd naar #general (als $IDENT)"
