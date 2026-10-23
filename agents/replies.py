# SPDX-License-Identifier: MIT
"""A reply addresses the agent it replies to (openspec change reply-to-message).

The relay stores a thread reply as `["e", <parent-id>, "", "reply"]`; older
clients wrote unmarked `e` tags, where the last one is the target (NIP-10).
The parent is looked up in the channel's own history only: a reply to a message
the listener cannot see addresses nobody.
"""


def parent_id(m):
    es = [t for t in (m or {}).get("tags") or [] if isinstance(t, list) and len(t) >= 2
          and t[0] == "e"]
    marked = [t[1] for t in es if len(t) >= 4 and t[3] == "reply"]
    if marked:
        return marked[-1]
    unmarked = [t[1] for t in es if len(t) < 4 or not t[3]]
    return unmarked[-1] if unmarked else None


def parent_of(m, msgs):
    """The message `m` replies to, from the same channel's history, or None."""
    pid = parent_id(m)
    return next((x for x in msgs or [] if x.get("id") == pid), None) if pid else None


def agent_of(parent, pub2name, agents):
    """The agent that wrote `parent`, when it is one this listener runs."""
    if not parent:
        return None
    h = pub2name.get(parent.get("pubkey"))
    return h if h in agents else None
