# SPDX-License-Identifier: EUPL-1.2
"""Identiteits- en ledenlogica, apart van buzzcli (relay-datalaag) zodat beide
onder de =<200-regel-conventie blijven. Namen komen uit de registry
(`identities.yml`) via de bestaande git-leeslaag, i.p.v. hardgecodeerd — zo dekt de
app alle identiteiten (agents én sessies), ook nieuwe.
"""
import re
import threading
import time

import github

_ID_TTL = 300       # geslaagde fetch: lang geldig
_ID_FAIL_TTL = 30   # mislukte fetch: kort negatief cachen (niet github hameren)
_lock = threading.Lock()
_cache = {"t": 0.0, "data": None, "ttl": 0}


def _parse_identities(text):
    """pubkey_hex -> {name, rol} uit de platte identities.yml (stdlib, geen yaml).
    Ingetrokken/niet-actieve identiteiten worden overgeslagen."""
    out = {}
    for m in re.finditer(r"^  ([A-Za-z0-9_-]+):\n((?:    .*\n?)*)", text, re.M):
        block = m.group(2)
        st = re.search(r"status:\s*(\S+)", block)
        if st and st.group(1).strip("'\"") != "actief":  # quotes strippen: 'actief'
            continue
        pk = re.search(r"pubkey_hex:\s*(\S+)", block)
        if not pk or pk.group(1) in ("null", "~"):
            continue
        rol = re.search(r"rol:\s*(\S+)", block)
        out[pk.group(1)] = {"name": m.group(1), "rol": rol.group(1) if rol else ""}
    return out


def identity_map():
    """pubkey_hex -> {name, rol}, gecachet uit identities.yml (git). author() roept
    dit per bericht aan, dus een MISLUKTE fetch mag github niet elke keer opnieuw
    raken: een fout wordt kort negatief gecachet (`_ID_FAIL_TTL`), en zolang er nog
    een geslaagde map is blijft die gelden. Geen dubbele HTTP-storm bij rate-limit."""
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
            # fetch faalde/leeg maar we hebben nog een goede map: die blijven serveren,
            # met een korte retry-venster i.p.v. elke call opnieuw github raken.
            _cache["t"], _cache["ttl"] = now, _ID_FAIL_TTL
        else:
            _cache.update(t=now, data={}, ttl=_ID_FAIL_TTL)
        return _cache["data"] or {}


def name_of(pubkey):
    """Registry-naam voor een pubkey, of None."""
    ident = identity_map().get(pubkey)
    return ident["name"] if ident else None


_AGENT_ROLES = ("chat-agent", "meta-agent")


def agent_pubkey(name):
    """pubkey_hex voor een AGENT-naam (chat-agent/meta-agent), of None. Case-
    insensitive. Bewust niet voor sessies (hubby/versum/…) of mark (rol: mens) —
    die hoor je niet via de mention-pop-up als bot toe te voegen. Gaat via
    chat_agents() zodat het bij een falende registry-fetch de _FALLBACK gebruikt
    i.p.v. iedereen als 'geen agent' te behandelen."""
    if not name:
        return None
    low = name.strip().lower()
    return next((a["pubkey"] for a in chat_agents() if a["handle"].lower() == low), None)


# Kern-agents als fallback: als de registry-fetch faalt (github down/rate-limit),
# blijft de 'per agent'-tab gevuld i.p.v. leeg. De registry is de primaire bron.
_FALLBACK = [
    {"handle": "assistent", "pubkey": "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255", "rol": "chat-agent"},
    {"handle": "architect", "pubkey": "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49", "rol": "chat-agent"},
    {"handle": "bouwer", "pubkey": "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74", "rol": "chat-agent"},
    {"handle": "marketing", "pubkey": "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64", "rol": "chat-agent"},
    {"handle": "ontwerper", "pubkey": "24ab03329773e12fb183d93e34e05485b3055246c12786e9cad46a311b5ed0e0", "rol": "chat-agent"},
    {"handle": "reviewer", "pubkey": "7734535c4a432cd0983b965af2ec3b1b07bb6308293e36590d8fdb00d95abff7", "rol": "chat-agent"},
    {"handle": "coordinator", "pubkey": "c14d1cdd1931061af176392f39fd17303591af0cef17d37e2aadf4bc2b36a8dc", "rol": "meta-agent"},
]


def chat_agents():
    """De chat-agents uit de registry (voor de 'per agent'-view), i.p.v. een
    hardgecodeerde lijst die achterloopt. Valt terug op _FALLBACK als de registry
    (nog) niet beschikbaar is, zodat de tab nooit stil leeg is."""
    agents = [{"handle": v["name"], "pubkey": pk, "rol": v["rol"]}
              for pk, v in sorted(identity_map().items(), key=lambda kv: kv[1]["name"])
              if v["rol"] in _AGENT_ROLES]
    return agents or _FALLBACK
