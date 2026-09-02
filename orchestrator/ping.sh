#!/usr/bin/env bash
# Post een bericht naar #general — de ping-lus met Mark in de app.
# Identiteit via env IDENT (default 'bouwer', zodat bestaande aanroepen blijven
# werken); bericht via arg of stdin. Geen secret in dit bestand: de nsec komt uit
# SOPS. De IDENT-filter weigert de mens-identiteit (rol mens) en niet-actieve
# identiteiten, zodat niemand zich als de mens (of ingetrokken) kan voordoen.
#   IDENT=hubby ~/boomhuis/orchestrator/ping.sh 'mijlpaal: ...'
set -euo pipefail
IDENT="${IDENT:-bouwer}"
MSG="${1:-$(cat)}"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# python3 -c: het programma staat in de arg (vast, geen shell-interpolatie), IDENT
# en ROOT gaan via env (geen injectie), en stdin blijft vrij voor de sops-pipe.
NPUB=$(IDENT="$IDENT" ROOT="$ROOT" python3 -c '
import os, sys, yaml
ident, root = os.environ["IDENT"], os.environ["ROOT"]
e = yaml.safe_load(open(root + "/identities.yml"))["identities"].get(ident)
if e is None:
    sys.stderr.write("onbekende IDENT %r (niet in identities.yml)\n" % ident); sys.exit(3)
if e.get("rol") == "mens":
    sys.stderr.write("IDENT %r is de mens-identiteit — niet toegestaan via ping.sh\n" % ident); sys.exit(4)
if e.get("status") != "actief":
    sys.stderr.write("IDENT %r is niet actief (status=%s)\n" % (ident, e.get("status"))); sys.exit(5)
print(e["npub"])')
GEN=$(ROOT="$ROOT" python3 -c 'import os,yaml;print(yaml.safe_load(open(os.environ["ROOT"]+"/channels.yml"))["channels"]["general"]["id"])')
NSEC=$(sops -d "$ROOT/secrets/identities.yaml" | IDENT="$IDENT" python3 -c 'import os,sys,yaml;print(yaml.safe_load(sys.stdin)["identities"][os.environ["IDENT"]]["nsec"])')

# Relay via de community-host 192.168.178.60 (de relay is community-scoped op DEZE
# host; het tailnet-IP geeft "no community configured for this host"). Vanaf een
# tailnet-node werkt dit via de subnet-router; override met env BUZZ_RELAY_URL.
# Eigen npub als --mention: staat vrije @-woorden toe (presentation-only).
BUZZ_PRIVATE_KEY="$NSEC" BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}" \
  ~/.local/bin/buzz messages send --channel "$GEN" --content - --mention "$NPUB" <<<"$MSG" >/dev/null
echo "[ping] verstuurd naar #general (als $IDENT)"
