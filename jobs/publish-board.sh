#!/usr/bin/env bash
# Maak de momentopname en zet 'm waar de chat 'm kan lezen.
#
# Twee stappen omdat die twee dingen op verschillende machines kunnen staan: de
# producent hoort bij de clones en de sessies (agent-lxc), het datavolume bij de
# chat (de relay-VM). Draait alles op één machine, dan laat je BOARD_SSH leeg en
# schrijft dit rechtstreeks.
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
  # Via het mountpoint van het volume: de chat draait non-root als uid 10001, dus
  # het bestand moet van hem zijn. Atomisch neerzetten (schrijven, dan mv) zodat
  # de app nooit een half bestand serveert.
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
