# SPDX-License-Identifier: MIT
"""The shared room (openspec change shared-room): the pure parts.

Mark, 2026-10-22: "I need to be able to talk to a bunch of agents at the same
time, see what they are doing, without pointing fingers" and "I want the agents
to work via git issues, so there's a reliable backtrack of what is being done."

A room is a channel with a `room:` block in channels.yml. Work in it is a
GitHub issue; the room only shows it. Which issue a message belongs to is read
from the room itself (the last `repo#N` an agent or the listener posted), not
kept in memory, so a listener restart loses nothing.
"""
import os
import re

import yaml

OWNER = "MWest2020"
MAX_HOPS = 3
# `ratatoskr#12`, as the listener appends it to every room line.
REF = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9._-]{0,99})#(\d{1,7})\b")
HANDOFF = re.compile(r"^!handoff\s+@?([a-z][a-z0-9_-]*)\s+(.+)$", re.M)
DONE = re.compile(r"^!done\s+(.+)$", re.M)


def load(root):
    """{channel name: room config}. A room needs members and repos; the first
    repo is the default. Anything else in channels.yml is not a room."""
    doc = yaml.safe_load(open(os.path.join(root, "channels.yml"))) or {}
    rooms = {}
    for name, ch in (doc.get("channels") or {}).items():
        r = (ch or {}).get("room")
        if r and r.get("members") and r.get("repos"):
            rooms[name] = {"members": list(r["members"]), "repos": list(r["repos"]),
                           "max_hops": int(r.get("max_hops", MAX_HOPS))}
    return rooms


def ref(repo, number):
    return f"{repo}#{number}"


def suffix(repo, number):
    """What the listener appends to every room line about an issue."""
    return f"\n\n· {ref(repo, number)}"


def find_ref(text, repos):
    """The last `repo#N` in `text` whose repo belongs to the room, or None."""
    hits = [(m.group(1), int(m.group(2))) for m in REF.finditer(text or "")
            if m.group(1) in repos]
    return hits[-1] if hits else None


def current_issue(content, earlier, repos, window=10):
    """The issue a human message continues: one named in the message itself,
    else the last one referenced in the room within `window` messages."""
    here = find_ref(content, repos)
    if here:
        return here
    for m in reversed(earlier[-window:]):
        hit = find_ref(m.get("content", ""), repos)
        if hit:
            return hit
    return None


def last_agent(earlier, members, pub2name, window=10):
    """The room member that spoke last within `window`, or None."""
    for m in reversed(earlier[-window:]):
        h = pub2name.get(m.get("pubkey"))
        if h in members:
            return h
    return None


def handoff(answer):
    """(target, line) from a `!handoff <agent> <line>` in the answer, or None."""
    m = HANDOFF.search(answer or "")
    return (m.group(1), m.group(2).strip()) if m else None


def done(answer):
    m = DONE.search(answer or "")
    return m.group(1).strip() if m else None


def clean(text):
    """The answer as the room shows it: without the room's markers."""
    text = HANDOFF.sub("", text or "")
    return DONE.sub("", text).strip()


def handoff_targets(contract, members, me):
    """Room members named in this agent's contract under "Hands off to". The
    listener checks a hand-off against the definition, not against the prompt."""
    line = next((ln for ln in (contract or "").splitlines()
                 if "hands off to" in ln.lower()), "")
    return [h for h in members if h != me and re.search(rf"\b{re.escape(h)}\b", line)]


def clause(room_name, room, handle, contract, repo, number, url):
    """What the agent is told about the room, generated from the config."""
    targets = handoff_targets(contract, room["members"], handle)
    hand = (f"To pass the work on, end with ONE line: `!handoff <agent> <what they "
            f"should do>`. Allowed: {', '.join(targets)}." if targets else
            "You hand nothing on to another agent in this room.")
    return (f"SHARED ROOM #{room_name}, with {', '.join(room['members'])} and Mark. "
            f"This work is tracked as {ref(repo, number)} ({url}); everything you "
            "write here is also recorded on that issue. Answer for your part only, "
            f"as your contract says. {hand} Only when your contract's 'Done when' is "
            "met, end with ONE line: `!done <the outcome in one line>`; that closes "
            "the issue. Waiting on Mark (a yes, a choice) is NOT done: then write no "
            "marker, the issue stays open and his answer continues it.")
