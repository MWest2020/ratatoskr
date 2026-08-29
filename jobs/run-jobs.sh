#!/usr/bin/env bash
# Wrapper: haal de post-identiteits-nsecs uit SOPS, exporteer als NSEC_<HANDLE>,
# en draai één job. Aangeroepen door de systemd-timer (boomhuis-job@<naam>).
set -euo pipefail
cd "$(dirname "$0")/.."          # boomhuis-root
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
export BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}"
export BUZZ_BIN="${BUZZ_BIN:-$HOME/.local/bin/buzz}"
export CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"

job="${1:?geef een jobnaam}"
# welke identiteit heeft deze job nodig?
who="$(python3 -c "import yaml,sys; print(yaml.safe_load(open('jobs/jobs.yml'))['jobs']['$job']['identity'])")"
dec="$(sops -d secrets/identities.yaml)"
nsec="$(printf '%s' "$dec" | awk "/  $who:/{f=1} f&&/nsec:/{print \$2; exit}")"
unset dec
export "NSEC_${who^^}=$nsec"
exec python3 jobs/run-job.py "$job"
