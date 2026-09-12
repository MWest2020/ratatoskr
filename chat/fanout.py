# SPDX-License-Identifier: EUPL-1.2
"""The views that fan out over every channel: message counts per channel and
who is in which channel.

buzzcli.py makes one relay call per function; these make one per channel, which
is why the two that the client polls are cached briefly behind a single-flight
lock. Reaches the relay through `buzzcli.` on purpose, not `from buzzcli import`,
so a stub on buzzcli reaches the fan-out too.
"""
import json
import subprocess
import threading
import time

import buzzcli
import roster  # identity/membership logic (names from identities.yml)


_OV_TTL = 15  # >= the client poll (12s) so one client really hits the cache
_ov_lock = threading.Lock()
_ov_cache = {"t": 0.0, "data": None}


def channel_overview():
    """{name, id, count} per channel through a buzz fan-out. Briefly cached with
    a single-flight lock: on a cold cache only one thread does the fan-out, the
    rest waits and gets the fresh result (no thundering herd)."""
    now = time.time()
    if _ov_cache["data"] is not None and now - _ov_cache["t"] < _OV_TTL:
        return _ov_cache["data"]
    with _ov_lock:
        # double-check inside the lock: another thread may just have refreshed
        now = time.time()
        if _ov_cache["data"] is not None and now - _ov_cache["t"] < _OV_TTL:
            return _ov_cache["data"]
        chans = buzzcli.list_channels()
        if not chans:
            # Empty is indistinguishable from a buzz failure → do NOT cache, and
            # signal it (the route gives 502). Otherwise the client prune would
            # wipe the read state on a momentary hiccup.
            raise RuntimeError("channel list empty or unreachable")
        out = []
        for name, cid in chans:
            try:
                rc, o, e = buzzcli.buzz(["messages", "get", "--channel", cid], timeout=8)
            except subprocess.TimeoutExpired:
                continue  # partial failure: skip the channel instead of count 0
            if rc != 0:
                continue
            try:
                raw = json.loads(o)
                msgs = raw if isinstance(raw, list) else raw.get("messages", [])
            except (ValueError, AttributeError):
                continue
            out.append({"name": name, "id": cid, "count": len(msgs)})
        _ov_cache["t"], _ov_cache["data"] = time.time(), out
        return out


def agent_roster():
    """Per (chat) agent from the registry: which channels it is in. Data from buzz."""
    membership = {name: buzzcli.channel_member_pubkeys(cid)
                  for name, cid in buzzcli.list_channels()}
    out = []
    for a in roster.chat_agents():
        chans = [name for name, mem in membership.items() if a["pubkey"] in mem]
        out.append({"handle": a["handle"], "rol": a["rol"], "channels": chans})
    return out


_cr_lock = threading.Lock()
_cr_cache = {"t": 0.0, "data": None}


def channel_roster():
    """Per channel: the real relay members with name and role (agents and
    sessions). That way Mark sees who is in a channel, including a session such as
    internetnl-cli. Cached for 15s (one buzz call per channel, like agent_roster)."""
    now = time.time()
    if _cr_cache["data"] is not None and now - _cr_cache["t"] < _OV_TTL:
        return _cr_cache["data"]
    with _cr_lock:  # single-flight, like channel_overview: one thread fans out
        now = time.time()
        if _cr_cache["data"] is not None and now - _cr_cache["t"] < _OV_TTL:
            return _cr_cache["data"]
        chans = buzzcli.list_channels()
        if not chans:
            # Empty is indistinguishable from a buzz failure → do NOT cache and
            # let the route 502 (like channel_overview), not a silent "no channels".
            raise RuntimeError("channel list empty or unreachable")
        idmap = roster.identity_map()
        out = []
        for name, cid in chans:
            members = []
            for pk, channel_role in buzzcli.channel_member_pubkeys(cid).items():
                if not pk:
                    continue  # member entry without a pubkey → no None key (TypeError)
                ident = idmap.get(pk) or {}
                members.append({
                    "name": ident.get("name") or buzzcli.NAMES.get(pk) or ("npub:" + pk[:8]),
                    "rol": ident.get("rol", ""),          # ecosystem role (agent/session/human)
                    "channel_role": channel_role,         # role on THIS channel (owner/bot/member)
                })
            members.sort(key=lambda m: (m["channel_role"] != "owner", m["name"]))
            out.append({"channel": name, "id": cid, "members": members})
        _cr_cache["t"], _cr_cache["data"] = time.time(), out
        return out
