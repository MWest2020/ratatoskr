# SPDX-License-Identifier: MIT
"""Which agents answer a human message, and why.

Pulled out of listener.py because it is the seam where three rules meet, and a
seam is where the failures live: two rules both claiming a message, or a weaker
one winning over a stronger one. Inline in the poll loop this could only be
tested by running the listener; here it is a pure function.

The order is the contract:

1. **mention** — an @handle of an agent that may speak here;
2. **follow-up** — no mention, but an agent spoke recently and this channel is
   in its own definition;
3. **default** — nobody named and nothing this channel may continue: the cold
   start of a channel that names a default agent. That includes the case where
   the most recent agent spoke here but may not follow up here.

Nothing answers an agent. That is checked by the caller (it skips agent
messages), and asserted here too, because "an agent answered an agent" is a
loop that costs money while it runs.
"""

FOLLOW_UP_WINDOW = 10


def pick(content, earlier, cname, agents, pub2name, may_speak, mentions,
         default_agent=None):
    """`(targets, reason)` for one human message.

    `earlier` are the messages before this one, oldest first; only the last
    `FOLLOW_UP_WINDOW` are considered. `may_speak(handle)` decides scope
    (handbook OR relay membership), `mentions(handle)` whether this text names
    that agent. Both are callables so this stays free of I/O.
    """
    named = [h for h in agents if mentions(h) and may_speak(h)]
    if named:
        return named, "mention"

    for prev in reversed(earlier[-FOLLOW_UP_WINDOW:]):
        handle = pub2name.get(prev.get("pubkey"))
        if handle is None:
            continue          # a human: keep looking further back
        # A follow-up stays definition-channel-only (spec); relay membership
        # only widens the mention branch above.
        if handle in agents and cname in (agents[handle].get("channels") or []):
            return [handle], "vervolg"
        # The most recent agent may not continue here (it answered a mention via
        # relay membership). Only it counts, so there is nothing to follow up:
        # treat it as a cold start. Stopping here meant nobody answered, which
        # looks exactly like a listener that is not running. Mark, 2026-09-23.
        break
    if default_agent:
        return [default_agent], "default"
    return [], ""
