#!/usr/bin/env bash
# Wat je draait NA elke uitrol. Drie lagen, in oplopende echtheid:
#
#   1. api.sh        — wat een vreemde niet mag (zonder sessie)
#   2. connection.sh — praat de chat met de relay (ingelogd, HTTP)
#   3. smoke.js      — doet de app het in een echte browser (ingelogd, JS)
#
# Waarom alle drie: op 2026-09-11 gaf laag 1 een halve dag 38/38 groen terwijl de
# app stilstond. Laag 1 raakt geen relay-code, laag 2 ziet geen JS, en alleen
# laag 3 ziet wat een mens ziet. Eén laag is geen test van een uitrol.
#
#   RATATOSKR_URL=https://… NAAM=… WW=… bash chat/e2e/after-deploy.sh
#
# smoke.js vergt Playwright + een Chromium; staat die elders, zet dan NODE_PATH
# en PW_CHROME (zie chat/e2e/README.md). Ontbreekt Playwright, dan zegt dit
# script dat hardop en faalt — een overgeslagen laag is geen groene uitrol.
set -u
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
