#!/usr/bin/env bash
# Install a pre-push guard in this clone: pushing to `main` runs verify.sh first.
#
# This is the gate, by choice. Mark does not want GitHub-side branch protection
# and has said so four times, so do not propose it again: the check runs where
# the pushes actually come from, which is this machine.
#
# It is a guard, not a fence. Someone determined can use --no-verify, and a
# writing work session has its own hooksPath and is unaffected (see
# agents/work_tree.py). What it stops is the real failure mode: pushing a red
# main by accident.
#
#   bash scripts/install_hooks.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$(git -C "$ROOT" rev-parse --git-path hooks)"
[ -d "$HOOKS" ] || HOOKS="$ROOT/$HOOKS"
mkdir -p "$HOOKS"

cat > "$HOOKS/pre-push" <<'HOOK'
#!/bin/sh
# Written by scripts/install_hooks.sh. Pushing to main runs verify.sh first.
root=$(git rev-parse --show-toplevel)
while read -r _local _lsha remote _rsha; do
    case "$remote" in
        refs/heads/main)
            echo "pre-push: main — verify.sh draaien..." >&2
            if ! (cd "$root" && bash verify.sh >/dev/null 2>&1); then
                echo "pre-push: GEWEIGERD — verify.sh is rood. Draai 'm zelf voor" >&2
                echo "          de reden, of push met --no-verify als je weet waarom." >&2
                exit 1
            fi
            ;;
    esac
done
exit 0
HOOK
chmod +x "$HOOKS/pre-push"
echo "pre-push-guard geïnstalleerd in $HOOKS"
