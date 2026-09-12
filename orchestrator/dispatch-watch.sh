#!/usr/bin/env bash
# Dispatch a habitat role run in a NAMED tmux session on jumpy, so you can read
# along live:   ssh jumpy -t tmux attach -t <session>
# Refreshes claude credentials from this host's Claude session first (fresh token).
#
#   Usage: dispatch-watch.sh <role> <change> <repo>
#   Env:   WORKER_IMAGE (pinned by default), HABITAT_BASE_BRANCH (reviewer/security),
#          CLAUDE_CREDS_FILE (default ~/.claude/.credentials.json)
set -euo pipefail
ROLE=${1:?role (architect|builder|reviewer|security)}
CHANGE=${2:?change name}
REPO=${3:?target repo (owner/repo)}
WORKER_IMAGE=${WORKER_IMAGE:-ghcr.io/mwest2020/habitat-worker:5ca93a0e2579e9e2932a7e618bae19ca7af3acc3}
BASE=${HABITAT_BASE_BRANCH:-}
CREDS=${CLAUDE_CREDS_FILE:-$HOME/.claude/.credentials.json}
JUMPY=${JUMPY:-jumpy}

# 1) refresh claude credentials (the subscription token expires after ~8h)
if [ -f "$CREDS" ]; then
  cat "$CREDS" | ssh -o BatchMode=yes "$JUMPY" \
    'f=$(mktemp); cat > "$f"; kubectl create secret generic claude-credentials -n agents --from-file=credentials.json="$f" --dry-run=client -o yaml | kubectl apply -f - >/dev/null; shred -u "$f" 2>/dev/null || rm -f "$f"'
  echo "[watch] claude credentials refreshed"
fi

# 2) dispatch scripts to jumpy (gone after a reboot; idempotent, so redo it)
ssh -o BatchMode=yes "$JUMPY" 'mkdir -p ~/habitat-dispatch'
scp -q ~/habitat/dispatch/dispatch.sh ~/habitat/dispatch/job-template.yaml "$JUMPY":~/habitat-dispatch/

# 3) named tmux session on jumpy (kubectl is local there), dispatch runs inside.
# All logic in a runner script → no nested quoting through tmux/ssh.
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
