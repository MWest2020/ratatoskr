#!/usr/bin/env bash
# Post a message to a boomhuis channel (default #general) — the ping loop.
# Env: IDENT = identity (default 'bouwer'; the human identity and inactive keys
# are refused). CHAN = target channel name from channels.yml (default 'general'),
# e.g. CHAN=review or CHAN=runs. The message comes from an arg or from stdin.
#   IDENT=reviewer CHAN=review ~/boomhuis/orchestrator/ping.sh 'verdict: ...'
# No secret in this file: the nsec comes from SOPS. The IDENT filter refuses the
# human identity (role mens) and inactive identities, so nobody can pose as the
# human (or as a revoked identity).
#   IDENT=hubby ~/boomhuis/orchestrator/ping.sh 'mijlpaal: ...'
set -euo pipefail
IDENT="${IDENT:-bouwer}"
CHAN="${CHAN:-general}"   # target channel (name from channels.yml), default #general
MSG="${1:-$(cat)}"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# python3 -c: the program is in the arg (fixed, no shell interpolation), IDENT
# and ROOT go through env (no injection), and stdin stays free for the sops pipe.
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
# #general is the hub channel: that is where Mark talks to odin, and to odin
# alone (Mark, 2026-09-07). A session reports in the project channel, or in
# #escalatie when a decision is needed — not in the hub.
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

# Relay through the community host 192.168.178.60 (the relay is community-scoped
# on THIS host; the tailnet IP gives "no community configured for this host").
# From a tailnet node this works through the subnet router; override with env
# BUZZ_RELAY_URL. Own npub as --mention: allows free @words (presentation-only).
BUZZ_PRIVATE_KEY="$NSEC" BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}" \
  ~/.local/bin/buzz messages send --channel "$CID" --content - --mention "$NPUB" <<<"$MSG" >/dev/null
echo "[ping] verstuurd naar #$CHAN (als $IDENT)"
