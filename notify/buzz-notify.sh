#!/usr/bin/env bash
# buzz-notify.sh — post habitat-run-gebeurtenissen naar het boomhuis (spec:
# run-notifications). BEST-EFFORT: een onbereikbare relay of een fout mag een
# run NOOIT vertragen of laten falen; elke fout wordt gelogd en we exit 0.
#
# Draait op de orchestrator-host (buiten de kooi). Vereist:
#   BUZZ_PRIVATE_KEY   nsec van de orchestrator-identiteit (uit boomhuis secrets)
#   BUZZ_RELAY_URL     bv. ws://192.168.178.60:3000  (default hieronder)
#   buzz               buzz-cli op PATH
#
# Gebruik (aangeroepen vanuit/naast dispatch.sh):
#   buzz-notify.sh run-start  <rol> <change> <repo> <run_id>
#   buzz-notify.sh run-end    <rol> <change> <repo> <run_id> <verdict> <branch> [rapportlink]
#   buzz-notify.sh escalate   <reden> [rapportlink]
#
# run-start opent een thread in #runs en print het root-event-id op stdout;
# run-end en escalate hangen als reply onder die thread als je het id doorgeeft
# via BUZZ_THREAD (env) — anders posten ze los.

set -uo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CHANNELS="$HERE/channels.yml"
LOG="${BUZZ_NOTIFY_LOG:-$HERE/notify/notify.log}"
export BUZZ_RELAY_URL="${BUZZ_RELAY_URL:-ws://192.168.178.60:3000}"

log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >> "$LOG" 2>/dev/null || true; }

# Kanaal-id opzoeken in channels.yml (geen yaml-parser nodig: platte lookup).
chan() {
  awk -v k="$1:" '$1==k{f=1;next} f&&$1=="id:"{print $2;exit}' "$CHANNELS"
}

# Best-effort post. Argumenten: <channel-id> <content> [reply-to-event-id]
# Print bij succes het nieuwe event-id op stdout; faalt stil (exit 0 blijft).
post() {
  local cid="$1" content="$2" reply="${3:-}"
  command -v buzz >/dev/null 2>&1 || { log "buzz-cli ontbreekt; skip"; return 0; }
  [ -n "${BUZZ_PRIVATE_KEY:-}" ] || { log "BUZZ_PRIVATE_KEY leeg; skip"; return 0; }
  [ -n "$cid" ] || { log "kanaal onbekend; skip"; return 0; }
  local args=(messages send --channel "$cid" --content "$content")
  [ -n "$reply" ] && args+=(--reply-to "$reply")
  local out
  if ! out=$(timeout 15 buzz "${args[@]}" 2>>"$LOG"); then
    log "post naar $cid mislukt (relay onbereikbaar?)"; return 0
  fi
  echo "$out" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("event_id",""))' 2>/dev/null
}

# Best-effort telefoon-push via de sender op agent-lxc. Mag een run NOOIT
# vertragen of laten falen: ontbrekende uv/sops → stil overslaan, altijd exit 0.
# Alleen aan als BUZZ_PUSH=1 (zo blijft run-start stil en pusht enkel wat telt:
# verdict + escalatie).
push_phone() {
  [ "${BUZZ_PUSH:-0}" = "1" ] || return 0
  command -v uv >/dev/null 2>&1 || { log "uv ontbreekt; geen push"; return 0; }
  local title="$1" url="$2" body="$3"
  # Op de ACHTERGROND (&): een push mag run-end/escalate nooit ophouden. Ruime
  # timeout (180s) want een koude uv-cache moet pywebpush + cryptography eerst
  # resolven; anders werd de eerste push na een cache-clear gekilld. Een non-
  # interactieve parent HUP't z'n achtergrond-kind niet bij normale exit, dus dit
  # overleeft de afronding van buzz-notify.sh. Alle uitvoer naar het log.
  ( cd "$HERE" && printf '%s' "$body" | timeout 180 uv run orchestrator/push-notify.py \
      --title "$title" --url "$url" >>"$LOG" 2>&1 || log "push-notify faalde (best-effort)" ) &
  return 0
}

cmd="${1:-}"; shift || true
case "$cmd" in
  run-start)
    rol="${1:-?}"; change="${2:-?}"; repo="${3:-?}"; run="${4:-?}"
    post "$(chan runs)" "🏗️ run gestart · rol=$rol · change=$change · repo=$repo · run=$run"
    ;;
  run-end)
    rol="${1:-?}"; change="${2:-?}"; repo="${3:-?}"; run="${4:-?}"
    verdict="${5:-?}"; branch="${6:-?}"; link="${7:-}"
    icon="✅"; [ "$verdict" != "PASS" ] && icon="❌"
    msg="$icon run klaar · rol=$rol · change=$change · verdict=$verdict · branch=$branch"
    [ -n "$link" ] && msg="$msg · rapport: $link"
    post "$(chan runs)" "$msg" "${BUZZ_THREAD:-}"
    push_phone "boomhuis · $verdict" "/" "$icon $change → $verdict (branch $branch)"
    ;;
  escalate)
    reden="${1:-?}"; link="${2:-}"
    msg="🚨 escalatie · $reden"
    [ -n "$link" ] && msg="$msg · rapport: $link"
    post "$(chan escalatie)" "$msg"
    push_phone "boomhuis · escalatie 🚨" "/" "$reden"
    ;;
  *)
    echo "gebruik: $0 {run-start|run-end|escalate} ..." >&2; exit 2 ;;
esac
exit 0
