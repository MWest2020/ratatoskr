#!/usr/bin/env bash
# Alles wat zonder de VM kan: unittests van de chat-backend en de listener.
# De end-to-end-tests draaien tegen de echte relay en zitten in chat/e2e/ —
# die staan hier bewust NIET in, zodat `verify.sh` ook offline groen is.
#
#   bash verify.sh
set -uo pipefail
cd "$(dirname "$0")"
fout=0
for map in chat agents; do
  echo "— $map"
  (cd "$map" && python3 -m unittest discover -p "test_*.py" 2>&1 | tail -3) || fout=1
done
echo
if [ $fout -eq 0 ]; then
  echo "verify: groen. End-to-end tegen de VM: zie chat/e2e/README.md"
else
  echo "verify: ROOD"
fi
exit $fout
