#!/bin/sh -e
# Rotatie identiteit 'mark' — relay-side stappen (openspec rotate-mark-identity).
# Draaien als root op vm 109: sudo /root/rotate-mark.sh
# Vereist: /root/mark-rotation.sec (nieuwe secret, hex, 0600) — wordt na afloop verwijderd.

NEW_PUB=a05339f005904935da71e0498f3d542ac223e8cdfac920c6152a743f91640769
OLD_PUB=821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db
NEW_SEC_FILE=/root/mark-rotation.sec
CHAT_ENV=/opt/buzz-build/chat/chat.env
CIDS="74504227-8f82-42d5-b943-e0bc059778bc c1a0db51-3c96-46f9-9afa-1f03acfd87a3 69cf0949-f1ab-4383-9627-8ef0f51977e1 b829eac4-a49b-4336-813e-90cdfa1a81c7 1ed0e697-7187-43ae-b0a1-faa667e1c93e b3b40816-ed50-4983-977b-44a3f8e9271f"

[ -s "$NEW_SEC_FILE" ] || { echo "FOUT: $NEW_SEC_FILE ontbreekt"; exit 1; }
NEW_SEC=$(cat "$NEW_SEC_FILE")
OLD_SEC=$(grep '^BUZZ_PRIVATE_KEY=' "$CHAT_ENV" | cut -d= -f2-)
export BUZZ_RELAY_URL=http://192.168.178.60:3000

echo "== 1/5 kanalen: nieuwe pubkey admin maken (als oude mark) =="
export BUZZ_PRIVATE_KEY="$OLD_SEC"
for CID in $CIDS; do
  printf '%s: ' "$CID"
  buzz channels add-member --channel "$CID" --pubkey "$NEW_PUB" --role admin && echo ok
done

echo "== 2/5 relay-owner flippen + relay herstarten =="
sed -i "s/^RELAY_OWNER_PUBKEY=.*/RELAY_OWNER_PUBKEY=$NEW_PUB/" /opt/buzz-relay/.env
docker compose -f /opt/buzz-relay/docker-compose.yml up -d relay
i=0; until [ "$(docker inspect -f '{{.State.Health.Status}}' buzz-prod-relay-1)" = healthy ]; do
  i=$((i+1)); [ $i -gt 36 ] && { echo "FOUT: relay niet healthy"; exit 1; }; sleep 5
done
echo "relay healthy"

echo "== 3/5 chat op nieuwe key =="
sed -i "s/^BUZZ_PRIVATE_KEY=.*/BUZZ_PRIVATE_KEY=$NEW_SEC/" "$CHAT_ENV"
systemctl restart boomhuis-chat
sleep 3
curl -sf http://localhost:8090/api/channels >/dev/null && echo "chat-API ok"

echo "== 4/5 verificatie nieuwe key =="
export BUZZ_PRIVATE_KEY="$NEW_SEC"
buzz channels members --channel 74504227-8f82-42d5-b943-e0bc059778bc | grep -q "$NEW_PUB" && echo "kanaal-membership ok"
buzz media get 4a64f32d2375ccfe44c0880416bc72b809b055f0fb7d9dddeb8bb3dd6b80c297.png -o /tmp/rot-test.png && rm /tmp/rot-test.png && echo "media-get ok"
curl -sf "http://localhost:8090/api/messages?channel=74504227-8f82-42d5-b943-e0bc059778bc" >/dev/null && echo "chat-messages ok"

echo "== 5/5 oude key eruit + afwijzingscheck =="
docker compose -f /opt/buzz-relay/docker-compose.yml exec -T relay buzz-admin remove-member --pubkey "$OLD_PUB"
export BUZZ_PRIVATE_KEY="$OLD_SEC"
if buzz channels list >/dev/null 2>&1; then
  echo "WAARSCHUWING: oude key werkt nog!"; exit 1
else
  echo "oude key geweigerd — correct"
fi
rm -f "$NEW_SEC_FILE"
echo "ROTATIE-KLAAR"
