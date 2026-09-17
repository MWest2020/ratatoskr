# SPDX-License-Identifier: MIT
"""Identity and membership logic, separate from buzzcli (the relay data layer) so
both stay under the ≤200-line convention. Names come from the registry
(`identities.yml`) through the existing git read layer instead of being
hard-coded — that way the app covers every identity (agents and sessions),
including new ones.
"""
import re
import threading
import time

import github

_ID_TTL = 300       # successful fetch: valid for a long time
_ID_FAIL_TTL = 30   # failed fetch: cache negatively, briefly (do not hammer github)
_lock = threading.Lock()
_cache = {"t": 0.0, "data": None, "ttl": 0}


def _parse_identities(text):
    """pubkey_hex -> {name, rol} from the flat identities.yml (stdlib, no yaml).
    Revoked or inactive identities are skipped."""
    out = {}
    for m in re.finditer(r"^  ([A-Za-z0-9_-]+):\n((?:    .*\n?)*)", text, re.M):
        block = m.group(2)
        st = re.search(r"status:\s*(\S+)", block)
        if st and st.group(1).strip("'\"") != "actief":  # strip quotes: 'actief'
            continue
        pk = re.search(r"pubkey_hex:\s*(\S+)", block)
        if not pk or pk.group(1) in ("null", "~"):
            continue
        rol = re.search(r"rol:\s*(\S+)", block)
        out[pk.group(1)] = {"name": m.group(1), "rol": rol.group(1) if rol else ""}
    return out


def identity_map():
    """pubkey_hex -> {name, rol}, cached from identities.yml (git). author() calls
    this per message, so a FAILED fetch must not hit github every single time: an
    error is cached negatively for a short while (`_ID_FAIL_TTL`), and as long as
    there is still a successful map that one keeps applying. No double HTTP storm
    on a rate limit."""
    now = time.time()
    with _lock:
        if _cache["data"] is not None and now - _cache["t"] < _cache["ttl"]:
            return _cache["data"]
    try:
        data = _parse_identities(github.get_file("identities.yml"))
    except Exception:
        data = None
    with _lock:
        if data:
            _cache.update(t=now, data=data, ttl=_ID_TTL)
        elif _cache["data"]:
            # the fetch failed or was empty but we still have a good map: keep
            # serving it, with a short retry window instead of hitting github on
            # every call.
            _cache["t"], _cache["ttl"] = now, _ID_FAIL_TTL
        else:
            _cache.update(t=now, data={}, ttl=_ID_FAIL_TTL)
        return _cache["data"] or {}


def name_of(pubkey):
    """Registry name for a pubkey, or None."""
    ident = identity_map().get(pubkey)
    return ident["name"] if ident else None


_AGENT_ROLES = ("chat-agent", "meta-agent")


def agent_pubkey(name):
    """pubkey_hex for an AGENT name (chat-agent/meta-agent), or None.
    Case-insensitive. Deliberately not for sessions (hubby/versum/…) or mark (role
    mens) — you should not add those as a bot through the mention pop-up. Goes
    through chat_agents() so that on a failing registry fetch it uses _FALLBACK
    instead of treating everyone as 'not an agent'."""
    if not name:
        return None
    low = name.strip().lower()
    return next((a["pubkey"] for a in chat_agents() if a["handle"].lower() == low), None)


def hub_pubkey():
    """pubkey_hex of the hub agent: the active identity with role `meta-agent`.

    Not by name, because the hub is renameable — `coordinator` became `odin` on
    2026-09-07, and a hard-coded name left every new channel without a hub
    (silently: the add is best effort). The role is the stable property.
    """
    return next((pk for pk, i in identity_map().items() if i.get("rol") == "meta-agent"), None)


# Core agents as a fallback: when the registry fetch fails (github down or rate
# limited), the 'per agent' tab stays filled instead of empty. The registry is the
# primary source.
_FALLBACK = [
    {"handle": "assistent", "pubkey": "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255", "rol": "chat-agent"},
    {"handle": "architect", "pubkey": "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49", "rol": "chat-agent"},
    {"handle": "bouwer", "pubkey": "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74", "rol": "chat-agent"},
    {"handle": "marketing", "pubkey": "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64", "rol": "chat-agent"},
    {"handle": "ontwerper", "pubkey": "24ab03329773e12fb183d93e34e05485b3055246c12786e9cad46a311b5ed0e0", "rol": "chat-agent"},
    {"handle": "reviewer", "pubkey": "7734535c4a432cd0983b965af2ec3b1b07bb6308293e36590d8fdb00d95abff7", "rol": "chat-agent"},
    {"handle": "odin", "pubkey": "b0e20b3080ca3a7d922800deb43c90b48ee0bd1f16cd546b87ccea7473b93ece", "rol": "meta-agent"},
]
# Note: _FALLBACK mirrors the LIVE registry (identities.yml on main): these seven
# agents. archivaris exists only on an unmerged branch and runs nowhere, so it
# does NOT belong here — otherwise the fallback would offer a non-live identity as
# addable during a registry outage.


def chat_agents():
    """The chat agents from the registry (for the 'per agent' view), instead of a
    hard-coded list that falls behind. Falls back on _FALLBACK when the registry is
    not (yet) available, so the tab is never silently empty."""
    agents = [{"handle": v["name"], "pubkey": pk, "rol": v["rol"]}
              for pk, v in sorted(identity_map().items(), key=lambda kv: kv[1]["name"])
              if v["rol"] in _AGENT_ROLES]
    return agents or _FALLBACK
