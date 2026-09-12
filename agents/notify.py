# SPDX-License-Identifier: EUPL-1.2
"""Push notification on a new message.

The existing push chain (orchestrator/push-notify.py → VAPID → phone) only fired
on run verdicts and escalations. Mark also wants to know THAT something is in a
channel, without keeping the app open.

What does NOT notify: his own messages (he wrote those), the ⋯ progress lines
(telemetry, not a message) and #statistics (likewise). What does: an agent answer
or a message from someone else.

At most one push per channel per COOLDOWN seconds; whatever arrives in that time
is counted and rides along on the next one ("+2 more"). Otherwise the phone
buzzes on every line of an agent that happens to answer three times.
"""
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER = os.path.join(ROOT, "orchestrator", "push-notify.py")
COOLDOWN = int(os.environ.get("PUSH_COOLDOWN_SECONDS", "45"))
SILENT = ("statistics",)          # channels that never push
PROGRESS_PREFIX = "⋯"

_last: dict = {}                # channel name -> (timestamp, suppressed count)


def should_notify(cname, author, content, me):
    """Is this a message a human has any use for?"""
    if cname in SILENT:
        return False
    if author == me:                       # own message
        return False
    if (content or "").lstrip().startswith(PROGRESS_PREFIX):
        return False
    return bool((content or "").strip())


def push(cname, author, content):
    """Send one notification; fails silently (it must never get in the way)."""
    now = time.time()
    t, missed = _last.get(cname, (0.0, 0))
    if now - t < COOLDOWN:
        _last[cname] = (t, missed + 1)     # inside the cooldown: only count
        return False
    body = (content or "").strip().replace("\n", " ")
    if len(body) > 140:
        body = body[:137] + "…"
    if missed:
        body += f"  (+{missed} eerder)"
    _last[cname] = (now, 0)
    try:
        # Channel in the URL: a notification about #bouw should land you in
        # #bouw, not on the app root (= the first channel). As a HASH, because
        # that never reaches the server and so adds no second cache entry in the sw.
        subprocess.run(["uv", "run", SENDER, "--title", f"#{cname} · {author}",
                        "--url", f"/#{cname}", "--body", body],
                       cwd=ROOT, capture_output=True, text=True, timeout=30)
        return True
    except Exception as e:                 # sender gone, network down, uv missing
        print(f"[listener] push mislukt (#{cname}): {e}", flush=True)
        return False
