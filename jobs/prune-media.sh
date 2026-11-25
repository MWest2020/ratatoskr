#!/usr/bin/env bash
# Delete images in buzz-media older than 30 days, then refuse to stay quiet if
# the bucket is still over MEDIA_MAX_BYTES — a size alarm that only logs would
# be the silent failure AGENTS.md forbids (design.md, "Retention: 30 days,
# then gone; loud above 2 GiB"). A message delete leaves the blob in place
# (design.md, "Measured on 2026-11-24"): this is the only thing that removes one.
#   bash jobs/prune-media.sh
set -euo pipefail
HOST="${MEDIA_PRUNE_SSH:-buzz-relay}"
DIR="${MEDIA_PRUNE_DIR:-/opt/buzz-relay}"
BUCKET="${BUZZ_S3_BUCKET:-buzz-media}"
MAX_BYTES="${MEDIA_MAX_BYTES:-2147483648}"   # 2 GiB
RUN="cd $DIR && sudo docker compose --profile maintenance run --rm media-prune"

ssh -o BatchMode=yes "$HOST" "$RUN"

JSON=$(ssh -o BatchMode=yes "$HOST" "$RUN size dst:$BUCKET --json")
BYTES=$(printf '%s' "$JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["bytes"])')

echo "[media-prune] $BUCKET: $BYTES bytes (grens $MAX_BYTES)"
if [ "$BYTES" -gt "$MAX_BYTES" ]; then
  echo "[media-prune] $BUCKET is $BYTES bytes, over de grens van $MAX_BYTES — dat is drukker dan verwacht (design.md, 'Expected volume'), geen bewuste groei" >&2
  exit 1
fi
