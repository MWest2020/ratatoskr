#!/usr/bin/env bash
# Alles wat zonder de VM kan: unittests, de regelgrens en de pins.
# De end-to-end-tests draaien tegen de echte relay en zitten in chat/e2e/ —
# die staan hier bewust NIET in, zodat `verify.sh` ook offline groen is.
#
#   bash verify.sh
set -uo pipefail
cd "$(dirname "$0")"
fout=0
for map in chat agents jobs orchestrator scripts; do
  echo "— $map"
  (cd "$map" && python3 -m unittest discover -p "test_*.py" 2>&1 | tail -3) || fout=1
done
echo "— regelgrens"
python3 scripts/line_limit.py || fout=1
echo "— pins"
python3 scripts/pin_check.py || fout=1
# Alleen lokaal: in CI bestaat ~/.config/systemd/user niet, en daar is geen host
# om van af te drijven.
if [ -d "$HOME/.config/systemd/user" ]; then
  echo "— units"
  python3 scripts/check_units.py || fout=1
  # Of ze ook wérken. check_units vergelijkt geïnstalleerd met git; een timer die
  # elke run omvalt blijft daar groen, want hij is keurig geïnstalleerd. Op
  # 2026-09-16 bleek er een 82 keer op rij gefaald te hebben zonder dat iets het
  # zei.
  echo "— timers"
  python3 scripts/check_timers.py || fout=1
fi
echo
if [ $fout -eq 0 ]; then
  echo "verify: groen. End-to-end tegen de VM: zie chat/e2e/README.md"
else
  echo "verify: ROOD"
fi
exit $fout
