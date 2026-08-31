#!/usr/bin/env bash
# Dispatch een habitat-rol-run in een NAMED tmux-sessie op jumpy, zodat je live
# kunt meelezen:   ssh jumpy -t tmux attach -t <sessie>
# Ververst eerst claude-credentials vanaf deze host's Claude-sessie (verse token).
#
#   Gebruik: dispatch-watch.sh <rol> <change> <repo>
#   Env:  WORKER_IMAGE (default gepind), HABITAT_BASE_BRANCH (reviewer/security),
#         CLAUDE_CREDS_FILE (default ~/.claude/.credentials.json)
set -euo pipefail
ROLE=${1:?rol (architect|builder|reviewer|security)}
CHANGE=${2:?change-naam}
REPO=${3:?doelrepo (owner/repo)}
WORKER_IMAGE=${WORKER_IMAGE:-ghcr.io/mwest2020/habitat-worker:5ca93a0e2579e9e2932a7e618bae19ca7af3acc3}
BASE=${HABITAT_BASE_BRANCH:-}
CREDS=${CLAUDE_CREDS_FILE:-$HOME/.claude/.credentials.json}
JUMPY=${JUMPY:-jumpy}

# 1) claude-credentials verversen (subscription-token verloopt ~8u)
if [ -f "$CREDS" ]; then
  cat "$CREDS" | ssh -o BatchMode=yes "$JUMPY" \
    'f=$(mktemp); cat > "$f"; kubectl create secret generic claude-credentials -n agents --from-file=credentials.json="$f" --dry-run=client -o yaml | kubectl apply -f - >/dev/null; shred -u "$f" 2>/dev/null || rm -f "$f"'
  echo "[watch] claude-credentials ververst"
fi

# 2) dispatch-scripts naar jumpy (na reboot weg; idempotent opnieuw)
ssh -o BatchMode=yes "$JUMPY" 'mkdir -p ~/habitat-dispatch'
scp -q ~/habitat/dispatch/dispatch.sh ~/habitat/dispatch/job-template.yaml "$JUMPY":~/habitat-dispatch/

# 3) named tmux-sessie op jumpy (kubectl is daar lokaal), dispatch draait erin.
# Alle logica in een runner-script → geen nested quoting door tmux/ssh heen.
slug=$(echo "$CHANGE" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | cut -c1-20 | sed 's/-*$//')
SESSION="hab-${ROLE}-${slug}"
RUNNER="run-${SESSION}.sh"
tmp=$(mktemp)
cat > "$tmp" <<EOF
#!/usr/bin/env bash
cd ~/habitat-dispatch
WORKER_IMAGE='$WORKER_IMAGE' CLAUDE_CREDS_FILE='' HABITAT_BASE_BRANCH='$BASE' \\
  bash dispatch.sh '$ROLE' '$CHANGE' '$REPO'
ec=\$?; echo; echo "[klaar — exit \$ec — druk enter om te sluiten]"; read
EOF
scp -q "$tmp" "$JUMPY":~/habitat-dispatch/"$RUNNER"
rm -f "$tmp"
ssh -o BatchMode=yes "$JUMPY" "chmod +x ~/habitat-dispatch/$RUNNER; tmux kill-session -t '$SESSION' 2>/dev/null; tmux new-session -d -s '$SESSION' 'bash ~/habitat-dispatch/$RUNNER'"

echo "SESSION=$SESSION"
echo "ATTACH=ssh jumpy -t tmux attach -t $SESSION"
