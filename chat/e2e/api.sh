#!/usr/bin/env bash
# End-to-end van de gate, tegen de VM: wat mag zonder sessie, en wat niet.
#
# Sinds `inloggen-per-persoon` zit ook lezen achter de sessie. Deze suite draait
# daarom bewust ZONDER cookie: hij bewijst dat er niets uitlekt aan wie niet
# ingelogd is. De ingelogde kant zit in chat/e2e/login-flow.js, want daar heb je
# een browser voor nodig.
H=${RATATOSKR_URL:-${BOOMHUIS_URL:-https://boomhuis-relay.tail8f7877.ts.net}}
ok=0; fail=0
t(){ # naam, verwachte code, curl-args...
  local naam=$1 verw=$2; shift 2
  local code; code=$(curl -sk -o /tmp/e2e.body -w '%{http_code}' --max-time 25 "$@")
  if [ "$code" = "$verw" ]; then ok=$((ok+1)); printf '  ok   %-42s %s\n' "$naam" "$code"
  else fail=$((fail+1)); printf '  FAIL %-42s kreeg %s, verwacht %s: %s\n' "$naam" "$code" "$verw" "$(head -c 90 /tmp/e2e.body)"; fi
}
echo "— statische shell"
for f in / /login /app.css /app.js /login.js /app-auth.js /app-cache.js /app-connection.js /app-modal.js /app-ui.js /app-push.js /sw.js /manifest.webmanifest /icon.svg /icon-192.png; do
  t "GET $f" 200 "$H$f"; done
t "GET /bestaat-niet" 404 "$H/bestaat-niet"

echo "— lezen zonder sessie: alles 401, en geen gegevens in het antwoord"
t "GET /api/channels"        401 "$H/api/channels"
t "GET /api/agents"          401 "$H/api/agents"
t "GET /api/channel-members" 401 "$H/api/channel-members"
t "GET /api/push/vapid"      401 "$H/api/push/vapid"
t "GET /api/overview"        401 "$H/api/overview"
t "GET /api/repos"           401 "$H/api/repos"
t "GET /api/prs (geldige repo)"   401 "$H/api/prs?repo=MWest2020/boomhuis"
t "GET /api/pr  (geldige repo)"   401 "$H/api/pr?repo=MWest2020/boomhuis&num=45"
t "GET /api/pinned?channel=netnl" 401 "$H/api/pinned?channel=netnl"

# De gate komt vóór het valideren van parameters: een vreemde krijgt overal
# hetzelfde 401 en kan dus niet eens uitproberen hoe de invoercontrole reageert.
# Dat die controle klópt staat in de unittests (chat/test_server.py), mét sessie.
for q in "prs?repo=boomhuis" "prs?repo=../etc" "prs" "pr?repo=MWest2020/boomhuis" \
         "pinned?channel=../../etc" "messages" "messages?channel=nietbestaand"; do
  t "GET /api/$q (gate vóór validatie)" 401 "$H/api/$q"; done

echo "— schrijven zonder sessie: alles 401, vóór de relay"
for p in /api/send /api/channels/create /api/channels/delete /api/channel/add-member /api/push/subscribe; do
  t "POST $p" 401 -X POST -H 'Content-Type: application/json' -d '{}' "$H$p"; done
t "POST /api/onbekend" 401 -X POST -H 'Content-Type: application/json' -d '{}' "$H/api/onbekend"

echo "— body-grens (16 KiB)"
t "POST met 20 KiB body" 413 -X POST -H 'Content-Type: application/json' \
  --data-binary "$(head -c 20000 /dev/zero | tr '\0' 'a')" "$H/api/send"

echo
echo "geslaagd=$ok mislukt=$fail"
[ "$fail" = 0 ]
