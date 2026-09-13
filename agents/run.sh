#!/usr/bin/env bash
# Start the multi-agent listener. Pulls every agent nsec out of the keystore and
# exports it as NSEC_<HANDLE> (in the process, not on disk).
#
# Which keystore is a choice of the INSTALLATION, not of this repo:
#   RATATOSKR_KEYSTORE=sops     (default — Mark's installation, needs the age key)
#   RATATOSKR_KEYSTORE=bestand  (a directory of 0600 files; see
#                                scripts/init_identities.py)
# A fresh installation elsewhere has neither Mark's secrets/ nor his age key, and
# taking them over would put two installations on one npub — which a relay reads
# as one identity contradicting itself.
set -euo pipefail
cd "$(dirname "$0")/.."          # boomhuis root
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
export BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}"
export BUZZ_BIN="${BUZZ_BIN:-$HOME/.local/bin/buzz}"
export CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"

# The reader identity: the orchestrator sees every channel (it owns them), an
# agent key only the channels that agent belongs to. Kept apart from the run
# list, because the orchestrator is no chat agent and is not spawned.
# Export the nsecs: NSEC_<HANDLE> for every agent in agents.yml, plus the
# orchestrator (the reader identity — it owns every channel, an agent key only
# sees the channels that agent belongs to).
#
# One line per handle through keystore.py, so both backends behave identically
# and a refusal carries its reason. A key that cannot be read is a agent that
# does not start; that is deliberate and the listener says so.
eval "$(python3 - <<'PYEOF'
import os, sys, yaml
sys.path.insert(0, "agents")
import keystore
handles = ["orchestrator"] + yaml.safe_load(open("agents/agents.yml"))["run"]
for h in handles:
    try:
        print(f'export NSEC_{h.upper()}={keystore.lees(h)}')
    except keystore.SleutelFout as e:
        print(f'[run.sh] geen sleutel voor {h}: {e}', file=sys.stderr)
PYEOF
)"
exec python3 agents/listener.py
