#!/usr/bin/env bash
# Start the multi-agent listener. Pulls the agent nsecs out of SOPS and exports
# them as NSEC_<HANDLE> (in the process, not on disk). Run on a host with
# claude + buzz + the age key (today: agent-lxc).
set -euo pipefail
cd "$(dirname "$0")/.."          # boomhuis root
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
export BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}"
export BUZZ_BIN="${BUZZ_BIN:-$HOME/.local/bin/buzz}"
export CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"

# The reader identity: the orchestrator sees every channel (it owns them), an
# agent key only the channels that agent belongs to. Kept apart from the run
# list, because the orchestrator is no chat agent and is not spawned.
# Export the nsecs: NSEC_<HANDLE> for every agent in agents.yml
dec="$(sops -d secrets/identities.yaml)"
for h in orchestrator $(python3 -c "import yaml; print(' '.join(yaml.safe_load(open('agents/agents.yml'))['run']))"); do
  nsec="$(printf '%s' "$dec" | awk "/  $h:/{f=1} f&&/nsec:/{print \$2; exit}")"
  export "NSEC_${h^^}=$nsec"
done
unset dec
exec python3 agents/listener.py
