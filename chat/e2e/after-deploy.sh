#!/usr/bin/env bash
# What you run AFTER every rollout. Three layers, in increasing realism:
#
#   1. api.sh        — what a stranger may not do (without a session)
#   2. connection.sh — does the chat talk to the relay (logged in, HTTP)
#   3. smoke.js      — does the app work in a real browser (logged in, JS)
#
# Why all three: on 2026-09-11 layer 1 was 38/38 green for half a day while the
# app stood still. Layer 1 touches no relay code, layer 2 sees no JS, and only
# layer 3 sees what a human sees. One layer is not a test of a rollout.
#
#   RATATOSKR_URL=https://… NAAM=… WW=… bash chat/e2e/after-deploy.sh
#
# smoke.js needs Playwright plus a Chromium; if those live elsewhere, set
# NODE_PATH and PW_CHROME (see chat/e2e/README.md). Without Playwright this script
# says so out loud and fails — a skipped layer is not a green rollout.
set -u
# pipefail: every layer below is piped into `tail`, and without this the exit
# status of the pipe is tail's -- always 0. On 2026-09-24 smoke.js reported
# "10 ok, 2 fail" and this script still printed "uitrol groen op alle drie de
# lagen". A gate that cannot fail is not a gate.
set -o pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
fout=0

echo "=== 1/3 api.sh (zonder sessie) ==="
bash "$HERE/api.sh" | tail -3 || fout=1

echo
echo "=== 2/3 connection.sh (ingelogd, relay) ==="
bash "$HERE/connection.sh" | tail -3 || fout=1

echo
echo "=== 3/3 smoke.js (echte browser) ==="
if node -e "require('playwright')" 2>/dev/null; then
  node "$HERE/smoke.js" | tail -9 || fout=1
else
  echo "  FAIL playwright niet gevonden — zet NODE_PATH naar een map met"
  echo "       playwright erin. Deze laag overslaan maakt de uitrol niet groen."
  fout=1
fi

echo
if [ "$fout" -eq 0 ]; then echo "uitrol groen op alle drie de lagen"; else echo "UITROL NIET GROEN"; fi
exit "$fout"
