# SPDX-License-Identifier: MIT
"""Who may start a habitat build from the chat, and how a chat message gets there.

Mark, 2026-11-14: "Dat moet wel kunnen. claude, odin, or jarvis mogen dit."
The list is `build_starters` in `agents/factory.yml`, so Mark controls it.
Without the key only the hub and the human may start one (the old rule).

Two roads lead to `try_build`:

- the hub's own generated answer (agent_turn.py, first line only);
- a chat message read by the listener's poll loop (`take` below): Mark's own
  message, anywhere in it, or an allowed agent identity's message, first line
  only. An agent's message is never answered as chat (no reply loop): only its
  marker is acted on.

What the listener itself posts is never input. odin's voice posts answers,
session reports and build lines with the hub's key; a session that pings as
odin signs with that same key. `OwnPosts` remembers what this process sent, so
a model-written line the listener posted can never start a build through the
poll loop.
"""
import collections


def allowed(cfg, hub, human):
    """The names that may start a build, in the order of the config."""
    names = (cfg or {}).get("build_starters")
    if names is None:
        names = [hub, human]
    return [str(n) for n in names if n]


def who(cfg, hub, human):
    """'mark, odin, claude or jarvis', for the refusal line."""
    names = allowed(cfg, hub, human)
    if len(names) < 2:
        return names[0] if names else "nobody"
    return ", ".join(names[:-1]) + " or " + names[-1]


def _key(text):
    return " ".join((text or "").split())


class OwnPosts:
    """Wraps `send(cid, content, nsec, npub)` and remembers what was sent."""

    def __init__(self, send, keep=500):
        self.send = send
        self.recent = collections.deque(maxlen=keep)

    def __call__(self, cid, content, nsec, npub):
        ok = self.send(cid, content, nsec, npub)
        if ok:
            self.recent.append(_key(content))
        return ok

    def __contains__(self, content):
        return _key(content) in self.recent


def take(m, writer, cname, cid, try_build, cfg, hub, human, own_posts=()):
    """Act on an allowed agent identity's `!build`. True: the message was an
    allowed agent's and is done, so the caller must not answer it as chat.
    Mark's own message is not handled here (False): his marker counts anywhere
    and his message is chat as usual. Agents off the list: False, and the
    caller ignores them as before."""
    if writer == human or writer not in allowed(cfg, hub, human):
        return False
    content = m.get("content", "")
    if content in own_posts:
        return True          # the listener's own post in the hub's voice
    try_build(content, writer, cname, cid, own=True)
    return True
