# SPDX-License-Identifier: EUPL-1.2
"""buzzcli — de buzz/relay-datalaag voor de chat-backend.

Praat via buzz-cli met de relay: kanalen, leden, berichten-counts, agent-roster.
Gescheiden van server.py (routing) zodat beide onder de 200-regel-invariant
blijven. Geen HTTP hier; puur data.
"""
import json
import os
import subprocess
import threading
import time

BUZZ = os.environ.get("BUZZ_BIN", "/usr/local/bin/buzz")

# Kanalen worden LIVE uit de relay gelezen (buzz channels list), zodat maken/
# verwijderen in de web-app meteen doorwerkt. #general staat vooraan.
def _channels_raw():
    """[{name, id, description}] uit de relay, gefilterd + gesorteerd."""
    rc, out, err = buzz(["channels", "list"])
    if rc != 0:
        return []
    try:
        d = json.loads(out)
    except Exception:
        return []
    c = d if isinstance(d, list) else d.get("channels", [])
    # De relay maakt zelf ondeletebare default-kanalen aan (een tweede 'general'
    # en 'welcome-everyone'); die filteren we weg. Voor 'general' houden we het
    # kanaal aan waar de agents in zitten.
    HIDE = {"welcome-everyone", "Welcome"}
    PREFER = {"general": "32ef5cd2-70d8-4b7e-9235-9692b8ab2a1c"}
    seen, rows = set(), []
    for x in c:
        name = x.get("name"); cid = x.get("channel_id") or x.get("id")
        if not name or not cid or name in HIDE:
            continue
        if name in PREFER and cid != PREFER[name]:
            continue  # sla het niet-voorkeurs-duplicaat over
        if name in seen:
            continue
        seen.add(name)
        rows.append({"name": name, "id": cid, "description": x.get("description") or ""})
    rows.sort(key=lambda r: (r["name"] != "general", r["name"]))  # general eerst, dan a-z
    return rows


def list_channels():
    """(name, id)-tuples — de interne vorm die overal gebruikt wordt."""
    return [(r["name"], r["id"]) for r in _channels_raw()]


def list_channels_meta():
    """[{name, id, description}] — voor de web-app (kanaal-beschrijvingen)."""
    return _channels_raw()


def valid_cid(cid):
    return any(i == cid for _, i in list_channels())

# pubkey -> weergavenaam
NAMES = {
    "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db": "mark",
    "27308f27bfdac7d051d6c79cbacffcf20eccc54abccb7495db68a58f25d083f0": "orchestrator",
    "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255": "assistent",
    "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49": "architect",
    "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74": "bouwer",
    "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64": "marketing",
}
ME = "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db"

# Bekende agents (uitbreidbaar: kopie met eigen identiteit + systemprompt).
AGENTS = [
    {"handle": "assistent",
     "pubkey": "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255",
     "rol": "algemene chat-agent"},
    {"handle": "architect",
     "pubkey": "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49",
     "rol": "architectuur-sparring"},
    {"handle": "bouwer",
     "pubkey": "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74",
     "rol": "bouw-agent (habitat)"},
    {"handle": "marketing",
     "pubkey": "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64",
     "rol": "marketing — usecases naar buiten"},
]


def buzz(args, stdin=None, timeout=25):
    p = subprocess.run([BUZZ, *args], capture_output=True, text=True,
                       input=stdin, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


# De canonieke identiteiten (agents én sessies) leven in identities.yml in de repo,
# niet hardgecodeerd hier. De VM-backend is stdlib-only en heeft het bestand niet
# lokaal, dus halen we het via de bestaande git-leeslaag (github.get_file) en parsen
# het stdlib. Gecachet zodat niet elke call GitHub raakt. NAMES blijft een fallback.
import re as _re

import github as _gh

_ID_TTL = 300
_id_lock = threading.Lock()
_id_cache = {"t": 0.0, "data": None}


def _parse_identities(text):
    """pubkey_hex -> {name, rol} uit de platte identities.yml (stdlib, geen yaml)."""
    out = {}
    for m in _re.finditer(r"^  ([A-Za-z0-9_-]+):\n((?:    .*\n?)*)", text, _re.M):
        block = m.group(2)
        pk = _re.search(r"pubkey_hex:\s*(\S+)", block)
        if not pk or pk.group(1) in ("null", "~"):
            continue
        rol = _re.search(r"rol:\s*(\S+)", block)
        out[pk.group(1)] = {"name": m.group(1), "rol": rol.group(1) if rol else ""}
    return out


def identity_map():
    """pubkey_hex -> {name, rol}, gecachet uit identities.yml (git). {} bij fout."""
    now = time.time()
    with _id_lock:
        if _id_cache["data"] is not None and now - _id_cache["t"] < _ID_TTL:
            return _id_cache["data"]
    try:
        data = _parse_identities(_gh.get_file("identities.yml"))
    except Exception:
        data = {}
    with _id_lock:
        _id_cache.update(t=now, data=data)
    return data


def author(pubkey):
    ident = identity_map().get(pubkey)
    if ident:
        return ident["name"]
    return NAMES.get(pubkey) or ("npub:" + pubkey[:8])


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


_OV_TTL = 15  # >= client-poll (12s) zodat één client de cache echt raakt
_ov_lock = threading.Lock()
_ov_cache = {"t": 0.0, "data": None}


def channel_overview():
    """Per kanaal {name, id, count} via buzz-fan-out. Kort gecachet met een
    single-flight-lock: bij een koude cache doet maar één thread de fan-out, de
    rest wacht en krijgt het verse resultaat (geen thundering herd)."""
    now = time.time()
    if _ov_cache["data"] is not None and now - _ov_cache["t"] < _OV_TTL:
        return _ov_cache["data"]
    with _ov_lock:
        # dubbel-check binnen de lock: een andere thread kan net ververst hebben
        now = time.time()
        if _ov_cache["data"] is not None and now - _ov_cache["t"] < _OV_TTL:
            return _ov_cache["data"]
        chans = list_channels()
        if not chans:
            # Leeg is niet te onderscheiden van een buzz-storing → NIET cachen en
            # signaleren (route geeft 502). Anders wist de client-prune de
            # leesstatus op een tijdelijke hik.
            raise RuntimeError("kanaallijst leeg of onbereikbaar")
        out = []
        for name, cid in chans:
            try:
                rc, o, e = buzz(["messages", "get", "--channel", cid], timeout=8)
            except subprocess.TimeoutExpired:
                continue  # deel-storing: kanaal overslaan i.p.v. als count 0 melden
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
    """Per agent: in welke kanalen (naam) hij zit, met rol. Data uit buzz."""
    membership = {name: channel_member_pubkeys(cid) for name, cid in list_channels()}
    roster = []
    for a in AGENTS:
        chans = [name for name, mem in membership.items() if a["pubkey"] in mem]
        roster.append({"handle": a["handle"], "rol": a["rol"], "channels": chans})
    return roster


_cr_lock = threading.Lock()
_cr_cache = {"t": 0.0, "data": None}


def channel_roster():
    """Per kanaal: de echte relay-leden met naam + rol (agents én sessies). Zo ziet
    Mark wie er in een kanaal zit, ook een sessie als internetnl-cli. 15s gecachet
    (per kanaal een buzz-call, net als agent_roster)."""
    now = time.time()
    with _cr_lock:
        if _cr_cache["data"] is not None and now - _cr_cache["t"] < _OV_TTL:
            return _cr_cache["data"]
    idmap = identity_map()
    out = []
    for name, cid in list_channels():
        members = []
        for pk, chrole in channel_member_pubkeys(cid).items():
            ident = idmap.get(pk) or {}
            members.append({
                "name": ident.get("name") or NAMES.get(pk) or ("npub:" + pk[:8]),
                "rol": ident.get("rol", ""),          # ecosysteem-rol (agent/sessie/mens)
                "channel_role": chrole,               # rol op dít kanaal (owner/bot/member)
            })
        members.sort(key=lambda m: (m["channel_role"] != "owner", m["name"]))
        out.append({"channel": name, "id": cid, "members": members})
    with _cr_lock:
        _cr_cache.update(t=now, data=out)
    return out
