#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Retention for message images (openspec agent-image-to-chat): delete image
# blobs older than 30 days from the relay's media store, then check the size.
#
# Runs on agent-lxc (ratatoskr-media-prune.timer) and reaches the relay VM over
# the same ssh+sudo route as publish-board.sh. The prune itself is the compose
# service `media-prune` (profile `maintenance`) in deploy/docker-compose.yml.
#
# Loud on purpose: a store still over MEDIA_MAX_BYTES after the prune exits 1, so
# the failing timer shows up in check_timers.py and in Mark's digest. A log line
# alone would be the silent failure AGENTS.md forbids.
#
#   bash jobs/prune-media.sh
#   MEDIA_SSH=buzz-relay MEDIA_MAX_BYTES=2147483648 bash jobs/prune-media.sh
set -euo pipefail
HOST="${MEDIA_SSH:-buzz-relay}"
DIR="${MEDIA_DIR:-/opt/buzz-relay}"
BUCKET="${MEDIA_BUCKET:-buzz-media}"
MAX="${MEDIA_MAX_BYTES:-2147483648}"   # 2 GiB; 20 images a day for 30 days is ~0.6 GiB
RUN="cd $DIR && sudo docker compose --profile maintenance run --rm media-prune"

echo "[media-prune] deleting images older than 30 days from $BUCKET on $HOST"
ssh -o BatchMode=yes "$HOST" "$RUN" \
  || { rc=$?; echo "[media-prune] prune failed on $HOST (rc=$rc)" >&2; exit 1; }

OUT=$(ssh -o BatchMode=yes "$HOST" "$RUN size dst:$BUCKET --json") \
  || { rc=$?; echo "[media-prune] size check failed on $HOST (rc=$rc)" >&2; exit 1; }
# rclone prints one JSON line, {"count":…,"bytes":…}; take the last line in case
# compose printed anything before it.
BYTES=$(printf '%s\n' "$OUT" | python3 -c '
import json, sys
lines = [ln for ln in sys.stdin.read().splitlines() if ln.strip()]
print(int(json.loads(lines[-1])["bytes"]))' 2>/dev/null) \
  || { echo "[media-prune] size check gave no byte count: ${OUT:0:200}" >&2; exit 1; }

if [ "$BYTES" -gt "$MAX" ]; then
  echo "[media-prune] media store is $BYTES bytes after the prune, over the MEDIA_MAX_BYTES" \
       "limit of $MAX: busier than expected, not deliberate growth; find out what uploads" >&2
  exit 1
fi
echo "[media-prune] media store is $BYTES bytes, under the limit of $MAX"
