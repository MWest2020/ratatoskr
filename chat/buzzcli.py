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

import roster  # identiteits-/ledenlogica (namen uit identities.yml)

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

# pubkey -> weergavenaam. Fallback als de registry-fetch faalt; bevat ook mark's
# PRE-rotatie-pubkey zodat berichten van vóór rotate-mark-identity nog "mark" tonen.
NAMES = {
    "a05339f005904935da71e0498f3d542ac223e8cdfac920c6152a743f91640769": "mark",
    "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db": "mark",
    "27308f27bfdac7d051d6c79cbacffcf20eccc54abccb7495db68a58f25d083f0": "orchestrator",
    "b0e20b3080ca3a7d922800deb43c90b48ee0bd1f16cd546b87ccea7473b93ece": "odin",
    "c14d1cdd1931061af176392f39fd17303591af0cef17d37e2aadf4bc2b36a8dc": "coordinator",  # ingetrokken sleutel; history blijft leesbaar
    "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255": "assistent",
    "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49": "architect",
    "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74": "bouwer",
    "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64": "marketing",
}
ME = "a05339f005904935da71e0498f3d542ac223e8cdfac920c6152a743f91640769"


# Kanaal-BEHEER (maken, verwijderen, leden) tekent als de orchestrator — een
# agent — en niet als `mark`. Zo zijn nieuwe kanalen agent-owned en hoeft de
# mens-sleutel nooit voor beheer gebruikt te worden (impersonatie-adjacent).
# Leeg = beheer uit: fail-closed met een duidelijke melding, NOOIT stil
# terugvallen op marks sleutel. Zie change reown-channels-to-orchestrator.
ORCH_KEY = os.environ.get("BUZZ_ORCHESTRATOR_KEY", "").strip()
ADMIN_OFF = "kanaalbeheer staat uit: BUZZ_ORCHESTRATOR_KEY ontbreekt op de server"


def buzz(args, stdin=None, timeout=25, key=None):
    """`key` overschrijft de ondertekenende sleutel (BUZZ_PRIVATE_KEY) voor deze
    ene aanroep. Zonder `key` tekent de procesidentiteit (mark) — dat blijft het
    pad voor berichten."""
    env = dict(os.environ, BUZZ_PRIVATE_KEY=key) if key else None
    p = subprocess.run([BUZZ, *args], capture_output=True, text=True,
                       input=stdin, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


def buzz_admin(args, stdin=None, timeout=25):
    """Kanaalbeheer als orchestrator. Geeft (None, ...) als er geen sleutel is."""
    if not ORCH_KEY:
        return None, "", ADMIN_OFF
    return buzz(args, stdin=stdin, timeout=timeout, key=ORCH_KEY)


def author(pubkey):
    # Namen komen uit de registry (roster.identity_map, uit identities.yml); NAMES
    # is een fallback als de git-fetch faalt.
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
    """Per (chat-)agent uit de registry: in welke kanalen hij zit. Data uit buzz."""
    membership = {name: channel_member_pubkeys(cid) for name, cid in list_channels()}
    out = []
    for a in roster.chat_agents():
        chans = [name for name, mem in membership.items() if a["pubkey"] in mem]
        out.append({"handle": a["handle"], "rol": a["rol"], "channels": chans})
    return out


_cr_lock = threading.Lock()
_cr_cache = {"t": 0.0, "data": None}


def channel_roster():
    """Per kanaal: de echte relay-leden met naam + rol (agents én sessies). Zo ziet
    Mark wie er in een kanaal zit, ook een sessie als internetnl-cli. 15s gecachet
    (per kanaal een buzz-call, net als agent_roster)."""
    now = time.time()
    if _cr_cache["data"] is not None and now - _cr_cache["t"] < _OV_TTL:
        return _cr_cache["data"]
    with _cr_lock:  # single-flight, net als channel_overview: één thread doet de fan-out
        now = time.time()
        if _cr_cache["data"] is not None and now - _cr_cache["t"] < _OV_TTL:
            return _cr_cache["data"]
        chans = list_channels()
        if not chans:
            # Leeg is niet te onderscheiden van een buzz-storing → NIET cachen en de
            # route 502 laten geven (zoals channel_overview), i.p.v. stil "geen kanalen".
            raise RuntimeError("kanaallijst leeg of onbereikbaar")
        idmap = roster.identity_map()
        out = []
        for name, cid in chans:
            members = []
            for pk, channel_role in channel_member_pubkeys(cid).items():
                if not pk:
                    continue  # lid-entry zonder pubkey → geen None-sleutel (TypeError)
                ident = idmap.get(pk) or {}
                members.append({
                    "name": ident.get("name") or NAMES.get(pk) or ("npub:" + pk[:8]),
                    "rol": ident.get("rol", ""),          # ecosysteem-rol (agent/sessie/mens)
                    "channel_role": channel_role,         # rol op dít kanaal (owner/bot/member)
                })
            members.sort(key=lambda m: (m["channel_role"] != "owner", m["name"]))
            out.append({"channel": name, "id": cid, "members": members})
        _cr_cache["t"], _cr_cache["data"] = time.time(), out
        return out
