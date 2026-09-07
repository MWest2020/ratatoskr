#!/usr/bin/env bash
# End-to-end van de LEES-kant + de auth-gate op alle schrijfroutes, tegen de VM.
H=https://boomhuis-relay.tail8f7877.ts.net
ok=0; fail=0
t(){ # naam, verwachte code, curl-args...
  local naam=$1 verw=$2; shift 2
  local code; code=$(curl -sk -o /tmp/e2e.body -w '%{http_code}' --max-time 25 "$@")
  if [ "$code" = "$verw" ]; then ok=$((ok+1)); printf '  ok   %-42s %s\n' "$naam" "$code"
  else fail=$((fail+1)); printf '  FAIL %-42s kreeg %s, verwacht %s: %s\n' "$naam" "$code" "$verw" "$(head -c 90 /tmp/e2e.body)"; fi
}
echo "— statische shell"
for f in / /index.html /app.css /app.js /app-auth.js /app-modal.js /app-ui.js /app-push.js /sw.js /manifest.webmanifest /icon.svg /icon-192.png; do
  t "GET $f" 200 "$H$f"; done
t "GET /bestaat-niet" 404 "$H/bestaat-niet"

echo "— lezen (open op het tailnet)"
t "GET /api/channels"        200 "$H/api/channels"
t "GET /api/agents"          200 "$H/api/agents"
t "GET /api/channel-members" 200 "$H/api/channel-members"
t "GET /api/push/vapid"      200 "$H/api/push/vapid"
t "GET /api/overview"        200 "$H/api/overview"
t "GET /api/repos"           200 "$H/api/repos"
t "GET /api/prs?repo=boomhuis" 200 "$H/api/prs?repo=boomhuis"
t "GET /api/prs (repo mist)" 400 "$H/api/prs"
t "GET /api/pr (num mist)"   400 "$H/api/pr?repo=boomhuis"
t "GET /api/pinned?channel=netnl" 200 "$H/api/pinned?channel=netnl"
t "GET /api/pinned (rare naam)"   200 "$H/api/pinned?channel=../../etc"
t "GET /api/messages (geen kanaal)" 400 "$H/api/messages"
t "GET /api/messages (onzin-cid)"   400 "$H/api/messages?channel=nietbestaand"

echo "— schrijven zonder apparaat-token: alles 401, vóór de relay"
for p in /api/send /api/channels/create /api/channels/delete /api/channel/add-member /api/push/subscribe; do
  t "POST $p" 401 -X POST -H 'Content-Type: application/json' -d '{}' "$H$p"; done
t "POST /api/onbekend" 401 -X POST -H 'Content-Type: application/json' -d '{}' "$H/api/onbekend"

echo "— body-grens (16 KiB)"
t "POST met 20 KiB body" 413 -X POST -H 'Content-Type: application/json' \
  --data-binary "$(head -c 20000 /dev/zero | tr '\0' 'a')" "$H/api/send"

echo
echo "geslaagd=$ok mislukt=$fail"
[ "$fail" = 0 ]
