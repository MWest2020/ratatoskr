#!/usr/bin/env bash
# Start de multi-agent listener. Haalt de agent-nsecs uit SOPS en exporteert ze
# als NSEC_<HANDLE> (in het proces, niet op schijf). Draai op een host met
# claude + buzz + de age-key (nu: agent-lxc).
set -euo pipefail
cd "$(dirname "$0")/.."          # boomhuis-root
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
export BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}"
export BUZZ_BIN="${BUZZ_BIN:-$HOME/.local/bin/buzz}"
export CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"

# nsecs exporteren: NSEC_<HANDLE> voor elke agent in agents.yml
dec="$(sops -d secrets/identities.yaml)"
for h in $(python3 -c "import yaml,sys; print(' '.join(yaml.safe_load(open('agents/agents.yml'))['agents']))"); do
  nsec="$(printf '%s' "$dec" | awk "/  $h:/{f=1} f&&/nsec:/{print \$2; exit}")"
  export "NSEC_${h^^}=$nsec"
done
unset dec
exec python3 agents/listener.py
