# SPDX-License-Identifier: MIT
"""Who may start a habitat build from the chat, and how a chat message gets there.

Mark, 2026-11-14: "Dat moet wel kunnen. claude, odin, or jarvis mogen dit."
The list is `build_starters` in `agents/factory.yml`, so Mark controls it.
Without the key only the hub and the human may start one (the old rule). A
name counts only while its identity in identities.yml is `actief`: a revoked
key starts nothing, even when it is still on the list.

Two roads lead to `try_build`:

- the hub's own generated answer (agent_turn.py, first line only);
- a chat message read by the listener's poll loop (`take` below): Mark's own
  message, anywhere in it, or an allowed agent identity's message, first line
  only. An agent's message is never answered as chat (no reply loop): only its
  marker is acted on.

What the listener itself posts is never input. odin's voice posts answers,
session reports and build lines with the hub's key; a session that pings as
odin signs with that same key. `OwnPosts` remembers what this process sends
(channel, signer, text), BEFORE the send: a send that times out may still have
been published, and its echo must not start a build.

An agent may retry on a refusal (jarvis is a model). The same refused marker
from the same agent starter is dropped for `QUIET` seconds: no gh call, no
channel line, a log line only.
"""
import collections
import os
import time

import yaml

import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUIET = 600          # seconds an identical refused marker of one agent stays dropped
_ids = {}            # identities.yml, read once (a revocation is a git change + restart)
_refused = {}        # (starter, repo, change, issue) -> time of the refusal
# Only refusals that cannot change within QUIET are throttled; "no change on main" (the
# spec PR may merge in a minute) or a GitHub hiccup is always answered (review, 2026-11-14).
LASTING = ("is not on the factory's list", "times today without a merge")


def identities(root=ROOT):
    if root not in _ids:
        with open(os.path.join(root, "identities.yml")) as fh:
            _ids[root] = (yaml.safe_load(fh) or {}).get("identities") or {}
    return _ids[root]


def allowed(cfg, hub, human, ids=None):
    """The names that may start a build, in the order of the config, active only."""
    ids = identities() if ids is None else ids
    names = (cfg or {}).get("build_starters")
    if names is None:
        names = [hub, human]
    return [str(n) for n in names
            if n and (ids.get(str(n)) or {}).get("status") == "actief"]


def who(cfg, hub, human, ids=None):
    """'mark, odin, claude or jarvis', for the refusal line."""
    names = allowed(cfg, hub, human, ids)
    if len(names) < 2:
        return names[0] if names else "nobody"
    return ", ".join(names[:-1]) + " or " + names[-1]


def _key(cid, npub, text):
    return (cid, npub, " ".join((text or "").split()))


class OwnPosts:
    """Wraps `send(cid, content, nsec, npub)` and remembers what was sent."""

    def __init__(self, send, keep=500):
        self.send = send
        self.recent = collections.deque(maxlen=keep)

    def __call__(self, cid, content, nsec, npub):
        # Before the send, whatever it returns: relay.sender says False on a
        # timeout or a non-zero exit even when the event was already published.
        # A false positive only ignores an identical post by the same key.
        self.recent.append(_key(cid, npub, content))
        return self.send(cid, content, nsec, npub)

    def seen(self, cid, npub, content):
        return _key(cid, npub, content) in self.recent


def take(m, writer, cname, cid, try_build, cfg, hub, human, own_posts=None,
         ids=None, refused=None, now=time.time, log=print):
    """Act on an allowed agent identity's `!build`. True: the message was an
    allowed agent's and is done, so the caller must not answer it as chat.
    Mark's own message is not handled here (False): his marker counts anywhere
    and his message is chat as usual. Agents off the list, or revoked: False,
    and the caller ignores them as before."""
    ids = identities() if ids is None else ids
    refused = _refused if refused is None else refused
    if writer == human or writer not in allowed(cfg, hub, human, ids):
        return False
    content = m.get("content", "")
    npub = (ids.get(writer) or {}).get("npub")
    if own_posts is not None and own_posts.seen(cid, npub, content):
        return True          # the listener's own post in the hub's voice
    mk = build.read_marker(content, own=True)
    key = (writer, mk[0].lower(), mk[1].lower(), mk[2]) if mk else None
    for k in [k for k, t in refused.items() if now() - t >= QUIET]:
        del refused[k]
    if key in refused:
        log(f"[listener] {writer}: same refused !build within {QUIET}s, dropped: "
            f"{mk[0]} {mk[1]}", flush=True)
        return True
    out = try_build(content, writer, cname, cid, own=True)
    if key and isinstance(out, str) and out.startswith("⛔") and any(r in out for r in LASTING):
        refused[key] = now()
    return True
