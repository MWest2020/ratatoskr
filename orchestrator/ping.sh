#!/usr/bin/env bash
# Post een bericht naar een boomhuis-kanaal (default #general) — de ping-lus.
# Env: IDENT = identiteit (default 'bouwer'; de mens-identiteit + niet-actieve
# sleutels worden geweigerd). CHAN = doelkanaal-naam uit channels.yml (default
# 'general'), bv. CHAN=review of CHAN=runs. Bericht via arg of stdin.
#   IDENT=reviewer CHAN=review ~/boomhuis/orchestrator/ping.sh 'verdict: ...' Geen secret in dit bestand: de nsec komt uit
# SOPS. De IDENT-filter weigert de mens-identiteit (rol mens) en niet-actieve
# identiteiten, zodat niemand zich als de mens (of ingetrokken) kan voordoen.
#   IDENT=hubby ~/boomhuis/orchestrator/ping.sh 'mijlpaal: ...'
set -euo pipefail
IDENT="${IDENT:-bouwer}"
CHAN="${CHAN:-general}"   # doelkanaal (naam uit channels.yml), default #general
MSG="${1:-$(cat)}"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# python3 -c: het programma staat in de arg (vast, geen shell-interpolatie), IDENT
# en ROOT gaan via env (geen injectie), en stdin blijft vrij voor de sops-pipe.
NPUB=$(IDENT="$IDENT" ROOT="$ROOT" CHAN="$CHAN" python3 -c '
import os, sys, yaml
ident, root = os.environ["IDENT"], os.environ["ROOT"]
e = yaml.safe_load(open(root + "/identities.yml"))["identities"].get(ident)
if e is None:
    sys.stderr.write("onbekende IDENT %r (niet in identities.yml)\n" % ident); sys.exit(3)
if e.get("rol") == "mens":
    sys.stderr.write("IDENT %r is de mens-identiteit — niet toegestaan via ping.sh\n" % ident); sys.exit(4)
if e.get("status") != "actief":
    sys.stderr.write("IDENT %r is niet actief (status=%s)\n" % (ident, e.get("status"))); sys.exit(5)
# #general is het hub-kanaal: daar praat Mark met odin, en met odin alleen
# (besluit Mark 2026-09-07). Een sessie rapporteert in het projectkanaal, of in
# #escalatie als er een besluit nodig is — niet in de hub.
if e.get("rol") == "sessie" and os.environ.get("CHAN", "general") == "general":
    sys.stderr.write("IDENT %r is een sessie: #general is hub-only (odin). "
                     "Kies CHAN=<projectkanaal> of CHAN=escalatie.\n" % ident); sys.exit(8)
print(e["npub"])')
CID=$(CHAN="$CHAN" ROOT="$ROOT" python3 -c '
import os, sys, yaml
ch = yaml.safe_load(open(os.environ["ROOT"] + "/channels.yml"))["channels"]
c = ch.get(os.environ["CHAN"])
if not c:
    sys.stderr.write("onbekend kanaal %r (niet in channels.yml)\n" % os.environ["CHAN"]); sys.exit(6)
cid = c.get("id")
if not cid:
    sys.stderr.write("kanaal %r heeft geen id in channels.yml\n" % os.environ["CHAN"]); sys.exit(7)
print(cid)')
NSEC=$(sops -d "$ROOT/secrets/identities.yaml" | IDENT="$IDENT" python3 -c 'import os,sys,yaml;print(yaml.safe_load(sys.stdin)["identities"][os.environ["IDENT"]]["nsec"])')

# Relay via de community-host 192.168.178.60 (de relay is community-scoped op DEZE
# host; het tailnet-IP geeft "no community configured for this host"). Vanaf een
# tailnet-node werkt dit via de subnet-router; override met env BUZZ_RELAY_URL.
# Eigen npub als --mention: staat vrije @-woorden toe (presentation-only).
BUZZ_PRIVATE_KEY="$NSEC" BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}" \
  ~/.local/bin/buzz messages send --channel "$CID" --content - --mention "$NPUB" <<<"$MSG" >/dev/null
echo "[ping] verstuurd naar #$CHAN (als $IDENT)"
