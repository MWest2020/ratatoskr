# SPDX-License-Identifier: EUPL-1.2
"""Relay topology for the listener: which channels exist and who is a member.
Separate from listener.py so that file stays under the ≤200-line convention. All
relay I/O goes through a supplied `run(args) -> stdout|""` callable — the
listener owns the buzz env — so this module stays pure and testable.

Both lookups are cached briefly (the poll loop runs every few seconds, but
topology rarely changes). An empty or failed fetch never overwrites an earlier
successful cache: fall back on what we had.
"""
import json
import time

TTL = 60  # seconds; topology rarely changes

# The relay creates undeletable default channels of its own (a second 'general',
# 'welcome-everyone'/'Welcome'); those do not belong in the poll set. Mirrors
# (deliberately duplicated: other dir, no shared import) the HIDE in
# chat/buzzcli.py. We need not copy the PREFER map there AS LONG AS channels.yml
# holds the canonical cids: those win on a name clash ({**live, **fallback}). If
# a name is missing from channels.yml, it falls back on the first relay record.
_HIDE = {"welcome-everyone", "Welcome"}

_channels = {"t": 0.0, "data": None}
_members = {}  # cid -> {"t": float, "pubs": set}


def _rows(out, key):
    """JSON list from relay output: a bare list or {<key>: [...]}. None when
    unparsable OR of an unexpected type (null/string/number) — the caller must
    not crash on .get(); that None means 'failed fetch'."""
    try:
        d = json.loads(out)
    except Exception:
        return None
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        v = d.get(key)  # absent (e.g. {"error":..}) OR not a list ({..}/"x") = failed
        return v if isinstance(v, list) else None
    return None


def poll_channels(run, fallback, now=None):
    """{name: cid} = channels.yml (`fallback`, curated and authoritative on cid)
    plus the genuinely new names from the live relay list. Junk channels
    (`_HIDE`) dropped. A failed or empty fetch does NOT overwrite an earlier
    successful cache (fall back on that cache; only without one on the bare
    fallback)."""
    now = time.time() if now is None else now
    if _channels["data"] is not None and now - _channels["t"] < TTL:
        return _channels["data"]
    rows = _rows(run(["channels", "list"]), "channels")
    if not rows:  # failed (None) OR empty — an empty channel list is never legit
        if _channels["data"] is not None:
            _channels["t"] = now          # keep the good cache, extend the window
            return _channels["data"]
        return dict(fallback)             # first failure: do NOT cache (like
                                          # members) → next tick tries again
    live = {}
    for x in rows:
        name, cid = x.get("name"), (x.get("channel_id") or x.get("id"))
        if name and cid and name not in _HIDE:
            live.setdefault(name, cid)  # dedup: first record per name
    # Dedup on NAME and CID: channels.yml (canonical) first, then the new relay
    # names. A channel that has the same cid under two names then appears only
    # once in the poll set (otherwise the listener would poll it twice).
    out, seen_cids = {}, set()
    for name, cid in list(fallback.items()) + list(live.items()):
        if name in out or cid in seen_cids:
            continue
        out[name] = cid
        seen_cids.add(cid)
    _channels.update(t=now, data=out)
    return out


def members(run, cid, now=None):
    """set of member pubkeys of a channel (relay), cached for ~TTL. Distinguishes
    a FAILED fetch (`None` → keep the good cache) from a genuinely EMPTY channel
    (`[]` → cache that, so 'last member gone' takes effect too)."""
    now = time.time() if now is None else now
    e = _members.get(cid)
    if e and now - e["t"] < TTL:
        return e["pubs"]
    rows = _rows(run(["channels", "members", "--channel", cid]), "members")
    if rows is None:  # failed fetch → keep earlier members; do NOT cache an empty
        if e:                          # entry without an earlier one (that would
            e["t"] = now               # mimic a truly empty channel for 60s)
            return e["pubs"]
        return set()
    pubs = {x.get("pubkey") for x in rows if x.get("pubkey")}  # succeeded (may be empty)
    _members[cid] = {"t": now, "pubs": pubs}
    return pubs


def is_scoped(def_channels, cname, agent_pub, member_pubs_fn):
    """Does an agent answer in this channel? Handbook scope OR relay membership
    (union). Pure (no I/O) so the core rule can be tested. `member_pubs_fn` is a
    0-arg callable — LAZY: only called when the handbook scope does not already
    answer the question, so we do no members fetch for a def-scoped channel."""
    return cname in def_channels or agent_pub in member_pubs_fn()


# Channels EVERY agent posts in, regardless of its own scope: the per-turn stats
# line and the limitation report. Without membership that send fails, and
# silently — visible only in the listener log. Observed 2026-09-07: odin was not
# in #statistics and five agents were not in #escalatie, so the escalation chain
# Mark asked for was dead in practice.
REPORT_CHANNELS = ("statistics", "escalatie")


def missing_memberships(agents, channels, name2pub, member_pubs_fn):
    """[(handle, channel name)] for every channel an agent posts in but is not a
    member of. Pure, on the supplied lookups, so it is testable without a relay."""
    out = []
    for handle, cfg in agents.items():
        pub = name2pub.get(handle)
        if not pub:
            continue
        for cname in dict.fromkeys(list(cfg.get("channels") or []) + list(REPORT_CHANNELS)):
            cid = channels.get(cname)
            if cid and pub not in member_pubs_fn(cid):
                out.append((handle, cname))
    return out
