#!/usr/bin/env bash
# Wrapper: pull the posting identity nsecs out of SOPS, export them as
# NSEC_<HANDLE>, and run one job. Called by the systemd timer (boomhuis-job@<name>).
set -euo pipefail
cd "$(dirname "$0")/.."          # boomhuis root
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
export BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}"
export BUZZ_BIN="${BUZZ_BIN:-$HOME/.local/bin/buzz}"
export CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"

job="${1:?geef een jobnaam}"
# which identity does this job need?
who="$(python3 -c "import yaml,sys; print(yaml.safe_load(open('jobs/jobs.yml'))['jobs']['$job']['identity'])")"
dec="$(sops -d secrets/identities.yaml)"
nsec="$(printf '%s' "$dec" | awk "/  $who:/{f=1} f&&/nsec:/{print \$2; exit}")"
unset dec
export "NSEC_${who^^}=$nsec"
exec python3 jobs/run-job.py "$job"
