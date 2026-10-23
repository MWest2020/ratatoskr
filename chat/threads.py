# SPDX-License-Identifier: MIT
"""Thread replies (openspec change reply-to-message), the pure part.

The relay stores a reply as `["e", <parent-id>, "", "reply"]` (NIP-10 with a
marker); measured on 2026-10-23. Older clients wrote unmarked `e` tags, where
the last one is the reply target (NIP-10's deprecated positional form).
"""
import re

EVENT_ID = re.compile(r"^[0-9a-f]{64}$")


def valid_event_id(s):
    return bool(EVENT_ID.match(s or ""))


def reply_parent(tags):
    """The id this event replies to, or None."""
    es = [t for t in tags or [] if isinstance(t, list) and len(t) >= 2 and t[0] == "e"]
    marked = [t[1] for t in es if len(t) >= 4 and t[3] == "reply"]
    if marked:
        return marked[-1]
    unmarked = [t[1] for t in es if len(t) < 4 or not t[3]]
    return unmarked[-1] if unmarked else None
