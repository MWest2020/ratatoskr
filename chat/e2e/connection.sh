#!/usr/bin/env bash
# Werkt de kant die api.sh NIET raakt: de relay-verbinding, ingelogd.
#
# Waarom dit bestaat: `api.sh` draait bewust zonder sessie en bewijst dat een
# vreemde niets krijgt. Daardoor raakt hij nooit één regel code die met de relay
# praat. Op 2026-09-11 draaide Marks installatie daardoor een halve dag met een
# chat die de relay niet kon bereiken ("404: no community is configured for this
# host", want de container sprak `relay:3000` aan terwijl de community op een
# andere host staat) — terwijl api.sh 38/38 groen gaf. Deze suite sluit dat gat.
#
#   RATATOSKR_URL=https://… NAAM=… WW=… bash chat/e2e/connection.sh
set -u
H=${RATATOSKR_URL:-${BOOMHUIS_URL:-https://boomhuis-relay.tail8f7877.ts.net}}
NAAM=${NAAM:-}; WW=${WW:-}
ok=0; fail=0
J=$(mktemp); trap 'rm -f "$J" /tmp/verb.body' EXIT

t(){ local naam=$1 verw=$2; shift 2
  local code; code=$(curl -sk -o /tmp/verb.body -w '%{http_code}' --max-time 25 "$@")
  if [ "$code" = "$verw" ]; then ok=$((ok+1)); printf '  ok   %-38s %s\n' "$naam" "$code"
  else fail=$((fail+1)); printf '  FAIL %-38s kreeg %s, verwacht %s: %s\n' "$naam" "$code" "$verw" "$(head -c 120 /tmp/verb.body)"; fi
}

if [ -z "$NAAM" ] || [ -z "$WW" ]; then
  echo "NAAM/WW ontbreken — inloggen kan niet, suite gestopt."; exit 2
fi

echo "— inloggen"
t "POST /api/login" 200 -c "$J" -X POST "$H/api/login" -H 'Content-Type: application/json' \
  -d "{\"naam\":\"$NAAM\",\"wachtwoord\":\"$WW\"}"

echo "— de relay-kant (dit is wat api.sh niet raakt)"
t "GET /api/channels" 200 -b "$J" "$H/api/channels"
# Een LEGE kanaallijst is geen geldige uitkomst op een draaiende installatie: dat
# is precies hoe een onbereikbare relay eruitziet.
if [ -s /tmp/verb.body ] && grep -q '"id"' /tmp/verb.body; then
  ok=$((ok+1)); printf '  ok   %-38s\n' "kanaallijst is niet leeg"
else
  fail=$((fail+1)); printf '  FAIL %-38s %s\n' "kanaallijst is LEEG" "$(head -c 120 /tmp/verb.body)"
fi
t "GET /api/overview" 200 -b "$J" "$H/api/overview"
t "GET /api/agents"   200 -b "$J" "$H/api/agents"

echo "— uitloggen"
t "POST /api/uitloggen" 200 -b "$J" -X POST "$H/api/uitloggen"
t "en dan is lezen weer dicht" 401 -b "$J" "$H/api/channels"

echo
echo "geslaagd=$ok mislukt=$fail"
[ "$fail" -eq 0 ]
