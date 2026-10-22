# SPDX-License-Identifier: MIT
"""Odin passes Mark's words to the coordinating Claude Code session.

Mark, 2026-10-22: the session asks him things through a Ratatoskr ping, but his
answer reached odin and stopped there — "odin should be able to tell you".

The road is the one `!route` takes, and for the same reason: odin POINTS at a
message (`!session <message id>`), the listener fetches it from the channel and
writes Mark's own text to an inbox file the session watches. Odin writes none of
it. Two checks the model cannot talk its way past:

- **Only the hub**, and only a message in the channel of this turn.
- **Only the human's own message**, by pubkey: an agent's text, or anyone
  else's, never reaches the session as if Mark had said it.
"""
import json
import os
import re
import time

import routing

MARKER = re.compile(r"^!session\s+([0-9a-f]{8,64})[ \t]*$", re.M | re.I)
INBOX = os.environ.get("RATATOSKR_SESSION_INBOX",
                       os.path.expanduser("~/.local/state/ratatoskr/session-inbox.jsonl"))


def read_marker(text):
    m = MARKER.search(text or "")
    return m.group(1).lower() if m else None


def strip_marker(text):
    return MARKER.sub("", text or "").strip()


def append(entry, path=None):
    """One JSON line, in a file only this user can read: it carries Mark's words
    to a session that acts on them."""
    path = path or INBOX
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle(answer, agent, hub, cname, msgs, pub2name, human, path=None, now=time.time):
    """Act on a `!session` marker; return the answer as the channel shows it."""
    mid = read_marker(answer)
    if not mid:
        return answer
    rest = strip_marker(answer)

    def refuse(why):
        return (rest + "\n\n" if rest else "") + f"(not passed to the session: {why})"

    if agent != hub:
        return refuse("only the hub passes messages to the session")
    msg = routing.find_message(msgs, mid)
    if msg is None:
        return refuse(f"no single message with id `{mid}` in this channel")
    writer = pub2name.get(msg.get("pubkey", ""))
    if writer != human:
        return refuse(f"that message is from {writer or 'someone unknown'}, not from {human}")
    append({"ts": int(now()), "from": writer, "channel": cname, "message_id": msg.get("id"),
            "text": (msg.get("content") or "").strip()}, path)
    return (rest + "\n\n" if rest else "") + "→ passed to the session, in your own words."


def clause(handle, hub):
    """What the hub is told; other agents hear nothing about it."""
    if handle != hub:
        return ""
    return ("\n\nWhen Mark wants something said to the CODING SESSION (the Claude Code "
            "session that builds and asks him questions by ping), do not repeat it "
            "yourself: end your answer with ONE line `!session <id of Mark's message>`. "
            "The listener passes his own message on, word for word; only his messages "
            "can be passed.")
