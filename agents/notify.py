# SPDX-License-Identifier: MIT
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

A message that carries an image (an `imeta` tag) notifies as `🖼 <caption>`,
never as its Markdown line with the media URL. The tags travel with the held-back
message through the cooldown, so a flushed image push reads the same.
"""
import importlib.util
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# By file path, not via sys.path: chat/ and orchestrator/ both have a board.py,
# and orchestrator/ is already on the listener's path (design.md, gap 7).
_spec = importlib.util.spec_from_file_location("imeta", os.path.join(ROOT, "chat", "imeta.py"))
imeta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imeta)
SENDER = os.path.join(ROOT, "orchestrator", "push-notify.py")
COOLDOWN = int(os.environ.get("PUSH_COOLDOWN_SECONDS", "45"))
SILENT = ("statistics",)          # channels that never push
PROGRESS_PREFIX = "⋯"

_last: dict = {}   # channel -> (timestamp, suppressed count, held (author, content, tags))


def should_notify(cname, author, content, me):
    """Is this a message a human has any use for?"""
    if cname in SILENT:
        return False
    if author == me:                       # own message
        return False
    if (content or "").lstrip().startswith(PROGRESS_PREFIX):
        return False
    return bool((content or "").strip())


def _body(content, missed, tags=None):
    """One notification line: the message, shortened, plus what rode along.
    An image message shows its caption behind 🖼, without the media URL."""
    if tags and imeta.from_tags(tags):   # no tags: imeta is not even asked
        content = "🖼 " + (imeta.clean_content(content, tags) or "image")
    body = (content or "").strip().replace("\n", " ")
    if len(body) > 140:
        body = body[:137] + "…"
    if missed:
        body += f"  (+{missed} eerder)"
    return body


def _send(cname, author, body):
    """Hand one notification to the sender. Never gets in the way: an exception
    is caught, and a sender that exits non-zero is NAMED — the three earlier
    breaks in this chain were all silent, and that is what made them expensive."""
    try:
        # Channel in the URL: a notification about #bouw should land you in
        # #bouw, not on the app root (= the first channel). As a HASH, because
        # that never reaches the server and so adds no second cache entry in the sw.
        r = subprocess.run(["uv", "run", SENDER, "--title", f"#{cname} · {author}",
                            "--url", f"/#{cname}", "--body", body],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print(f"[listener] push-sender rc={r.returncode} (#{cname}): "
                  f"{(r.stderr or r.stdout).strip()[:200]}", flush=True)
            return False
        return True
    except Exception as e:                 # sender gone, network down, uv missing
        print(f"[listener] push mislukt (#{cname}): {e}", flush=True)
        return False


def on_message(cname, author, event, me):
    """The listener's one call per new relay event (`buzz messages get` shape).
    Reads content and tags here, so the listener does not know the tag format.
    Tags that cannot be read cost the image marker, never the notification."""
    content = event.get("content", "")
    if not should_notify(cname, author, content, me):
        return False
    tags = event.get("tags")
    try:
        _body(content, 0, tags)
    except Exception as e:
        print(f"[listener] notify: image tags unreadable ({e})", flush=True)
        tags = None
    return push(cname, author, content, tags)


def push(cname, author, content, tags=None):
    """Send one notification; fails silently (it must never get in the way)."""
    now = time.time()
    t, missed, _held = _last.get(cname, (0.0, 0, None))
    if now - t < COOLDOWN:
        # Inside the cooldown: hold on to THIS message (the newest) and count the
        # rest. `flush` delivers it as soon as the cooldown expires. Before, the
        # message evaporated and only a counter rode along on the NEXT push in
        # that channel — measured 2026-09-18: a "(+1 eerder)" from four days
        # earlier. A notification that late is the same as no notification.
        _last[cname] = (t, missed + 1, (author, content, tags))
        return False
    _last[cname] = (now, 0, None)
    return _send(cname, author, _body(content, missed, tags))


def flush(now=None):
    """Deliver per channel the message the cooldown held back, as soon as that
    cooldown has expired. The listener calls this every poll tick. Returns the
    channel names that were sent (for the tests)."""
    now = time.time() if now is None else now
    sent = []
    for cname, (t, missed, held) in list(_last.items()):
        if not held or now - t < COOLDOWN:
            continue
        author, content, tags = held
        _last[cname] = (now, 0, None)
        # missed counts the held-back messages INCLUDING this one; the "+n"
        # names only the ones that do not get their own line.
        if _send(cname, author, _body(content, missed - 1, tags)):
            sent.append(cname)
    return sent
