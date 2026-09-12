#!/usr/bin/env bash
# Build the snapshot and put it where the chat can read it.
#
# Two steps because those two things can live on different machines: the producer
# belongs with the clones and the sessions (agent-lxc), the data volume with the
# chat (the relay VM). If everything runs on one machine, leave BOARD_SSH empty
# and this writes directly.
#
#   BOARD_OUT=/var/lib/ratatoskr/board.json bash jobs/publish-board.sh
#   BOARD_SSH=buzz-relay BOARD_VOLUME=buzz-prod_ratatoskr-chat-data bash jobs/publish-board.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

python3 "$HERE/board.py" --out "$TMP"

if [ -n "${BOARD_SSH:-}" ]; then
  VOL="${BOARD_VOLUME:?zet BOARD_VOLUME als je BOARD_SSH gebruikt}"
  # Through the volume's mountpoint: the chat runs non-root as uid 10001, so the
  # file has to belong to it. Placed atomically (write, then mv) so the app never
  # serves half a file.
  ssh -o BatchMode=yes "$BOARD_SSH" "sudo sh -c '
    v=\$(docker volume inspect -f \"{{.Mountpoint}}\" $VOL) || exit 1
    cat > \$v/board.json.tmp && chown 10001:10001 \$v/board.json.tmp &&
    mv \$v/board.json.tmp \$v/board.json'" < "$TMP"
  echo "[board] geplaatst op $BOARD_SSH:$VOL"
else
  DEST="${BOARD_OUT:-/var/lib/ratatoskr/board.json}"
  install -m 0644 "$TMP" "$DEST"
  echo "[board] geschreven naar $DEST"
fi
