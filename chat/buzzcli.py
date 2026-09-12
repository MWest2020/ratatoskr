# SPDX-License-Identifier: EUPL-1.2
"""buzzcli — the buzz/relay data layer for the chat backend.

Talks to the relay through the buzz CLI: channels, members, message counts, agent
roster. Separate from server.py (routing) so both stay under the 200-line
invariant. No HTTP here; data only.
"""
import json
import os
import subprocess
import threading
import time

import roster  # identiteits-/ledenlogica (namen uit identities.yml)

BUZZ = os.environ.get("BUZZ_BIN", "/usr/local/bin/buzz")

# Channels are read LIVE from the relay (buzz channels list), so creating and
# deleting in the web app takes effect at once. #general comes first.
def _channels_raw():
    """[{name, id, description}] from the relay, filtered and sorted."""
    rc, out, err = buzz(["channels", "list"])
    if rc != 0:
        return []
    try:
        d = json.loads(out)
    except Exception:
        return []
    c = d if isinstance(d, list) else d.get("channels", [])
    # The relay creates undeletable default channels of its own (a second
    # 'general' and 'welcome-everyone'); we filter those out. For 'general' we
    # keep the channel the agents are in.
    HIDE = {"welcome-everyone", "Welcome"}
    PREFER = {"general": "32ef5cd2-70d8-4b7e-9235-9692b8ab2a1c"}
    seen, rows = set(), []
    for x in c:
        name = x.get("name"); cid = x.get("channel_id") or x.get("id")
        if not name or not cid or name in HIDE:
            continue
        if name in PREFER and cid != PREFER[name]:
            continue  # skip the non-preferred duplicate
        if name in seen:
            continue
        seen.add(name)
        rows.append({"name": name, "id": cid, "description": x.get("description") or ""})
    rows.sort(key=lambda r: (r["name"] != "general", r["name"]))  # general first, then a-z
    return rows


def list_channels():
    """(name, id) tuples — the internal form used everywhere."""
    return [(r["name"], r["id"]) for r in _channels_raw()]


def list_channels_meta():
    """[{name, id, description}] — for the web app (channel descriptions)."""
    return _channels_raw()


def valid_cid(cid):
    return any(i == cid for _, i in list_channels())

# pubkey -> display name. A fallback when the registry fetch fails; also holds
# mark's PRE-rotation pubkey so pre-rotate-mark-identity messages show "mark".
NAMES = {
    "a05339f005904935da71e0498f3d542ac223e8cdfac920c6152a743f91640769": "mark",
    "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db": "mark",
    "27308f27bfdac7d051d6c79cbacffcf20eccc54abccb7495db68a58f25d083f0": "orchestrator",
    "b0e20b3080ca3a7d922800deb43c90b48ee0bd1f16cd546b87ccea7473b93ece": "odin",
    "c14d1cdd1931061af176392f39fd17303591af0cef17d37e2aadf4bc2b36a8dc": "coordinator",  # revoked key; history stays readable
    "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255": "assistent",
    "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49": "architect",
    "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74": "bouwer",
    "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64": "marketing",
}
ME = "a05339f005904935da71e0498f3d542ac223e8cdfac920c6152a743f91640769"


# Channel MANAGEMENT (create, delete, members) signs as the orchestrator — an
# agent — and not as `mark`. That way new channels are agent-owned and the human
# key never has to be used for management (impersonation-adjacent). Empty =
# management off: fail-closed with a clear message, NEVER a silent fallback on
# mark's key. See change reown-channels-to-orchestrator.
ORCH_KEY = os.environ.get("BUZZ_ORCHESTRATOR_KEY", "").strip()
ADMIN_OFF = "channel management is off: BUZZ_ORCHESTRATOR_KEY is missing on the server"


def buzz(args, stdin=None, timeout=25, key=None):
    """`key` overrides the signing key (BUZZ_PRIVATE_KEY) for this one call.
    Without `key` the process identity (mark) signs — that stays the path for
    messages."""
    env = dict(os.environ, BUZZ_PRIVATE_KEY=key) if key else None
    p = subprocess.run([BUZZ, *args], capture_output=True, text=True,
                       input=stdin, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


def buzz_admin(args, stdin=None, timeout=25):
    """Channel management as orchestrator. Returns (None, ...) when no key."""
    if not ORCH_KEY:
        return None, "", ADMIN_OFF
    return buzz(args, stdin=stdin, timeout=timeout, key=ORCH_KEY)


def author(pubkey):
    # Names come from the registry (roster.identity_map, from identities.yml);
    # NAMES is a fallback when the git fetch fails.
    return roster.name_of(pubkey) or NAMES.get(pubkey) or ("npub:" + pubkey[:8])


def channel_member_pubkeys(cid):
    rc, out, err = buzz(["channels", "members", "--channel", cid])
    if rc != 0:
        return {}
    try:
        d = json.loads(out)
    except Exception:
        return {}
    m = d if isinstance(d, list) else d.get("members", [])
    return {x.get("pubkey"): x.get("role") for x in m}


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
        chans = list_channels()
        if not chans:
            # Empty is indistinguishable from a buzz failure → do NOT cache, and
            # signal it (the route gives 502). Otherwise the client prune would
            # wipe the read state on a momentary hiccup.
            raise RuntimeError("channel list empty or unreachable")
        out = []
        for name, cid in chans:
            try:
                rc, o, e = buzz(["messages", "get", "--channel", cid], timeout=8)
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
    membership = {name: channel_member_pubkeys(cid) for name, cid in list_channels()}
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
        chans = list_channels()
        if not chans:
            # Empty is indistinguishable from a buzz failure → do NOT cache and
            # let the route 502 (like channel_overview), not a silent "no channels".
            raise RuntimeError("channel list empty or unreachable")
        idmap = roster.identity_map()
        out = []
        for name, cid in chans:
            members = []
            for pk, channel_role in channel_member_pubkeys(cid).items():
                if not pk:
                    continue  # member entry without a pubkey → no None key (TypeError)
                ident = idmap.get(pk) or {}
                members.append({
                    "name": ident.get("name") or NAMES.get(pk) or ("npub:" + pk[:8]),
                    "rol": ident.get("rol", ""),          # ecosystem role (agent/session/human)
                    "channel_role": channel_role,         # role on THIS channel (owner/bot/member)
                })
            members.sort(key=lambda m: (m["channel_role"] != "owner", m["name"]))
            out.append({"channel": name, "id": cid, "members": members})
        _cr_cache["t"], _cr_cache["data"] = time.time(), out
        return out
