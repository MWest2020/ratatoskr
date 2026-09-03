# SPDX-License-Identifier: EUPL-1.2
"""Relay-topologie voor de listener: welke kanalen bestaan en wie is waar lid.
Apart van listener.py zodat die onder de ≤200-regel-conventie blijft. Alle
relay-I/O loopt via een meegegeven `run(args) -> stdout|""`-callable — de listener
bezit de buzz-env — zodat deze module puur en testbaar blijft.

Beide lookups worden kort gecachet (de poll-lus draait elke paar seconden, maar
topologie verandert zelden). Een lege/mislukte fetch overschrijft nooit een
eerder geslaagde cache: val terug op wat we hadden.
"""
import json
import time

TTL = 60  # seconden; topologie verandert zelden

# De relay maakt zelf ondeletebare default-kanalen aan (een tweede 'general',
# 'welcome-everyone'/'Welcome'); die horen niet in de poll-set. Spiegelt de HIDE
# in chat/buzzcli.py:_channels_raw. De PREFER-map daar (general -> de juiste cid)
# hoeven we NIET te kopiëren: channels.yml is de gecureerde bron en wint bij een
# naam-botsing ({**live, **fallback}), dus de channels.yml-'general'-cid (waar de
# agents in zitten) is sowieso wat we pollen; de relay voegt alléén nieuwe namen toe.
_HIDE = {"welcome-everyone", "Welcome"}

_channels = {"t": 0.0, "data": None}
_members = {}  # cid -> {"t": float, "pubs": set}


def _rows(out, key):
    """JSON-lijst uit relay-output: kale lijst of {<key>: [...]}."""
    try:
        d = json.loads(out)
    except Exception:
        return None
    return d if isinstance(d, list) else d.get(key, [])


def poll_channels(run, fallback, now=None):
    """{name: cid} = channels.yml (`fallback`, gecureerd + autoritair op cid) plus
    de echt-nieuwe namen uit de live relay-lijst. Junk-kanalen (`_HIDE`) eruit. Een
    mislukte/lege fetch overschrijft een eerder geslaagde cache NIET (val terug op
    die cache; alleen zonder cache op de kale fallback)."""
    now = time.time() if now is None else now
    if _channels["data"] is not None and now - _channels["t"] < TTL:
        return _channels["data"]
    rows = _rows(run(["channels", "list"]), "channels")
    if rows is None:  # fetch faalde → goede cache behouden, anders kale fallback
        data = _channels["data"] if _channels["data"] is not None else dict(fallback)
        _channels.update(t=now, data=data)
        return data
    live = {}
    for x in rows:
        name, cid = x.get("name"), (x.get("channel_id") or x.get("id"))
        if name and cid and name not in _HIDE:
            live.setdefault(name, cid)  # dedup: eerste record per naam
    merged = {**live, **fallback}  # channels.yml-cid wint bij naam-botsing
    _channels.update(t=now, data=merged)
    return merged


def members(run, cid, now=None):
    """set van member-pubkeys van een kanaal (relay), ~TTL gecachet. Onderscheidt
    een MISLUKTE fetch (`None` → goede cache behouden) van een echt LEEG kanaal
    (`[]` → dat cachen, zodat 'laatste lid weg' ook doorwerkt)."""
    now = time.time() if now is None else now
    e = _members.get(cid)
    if e and now - e["t"] < TTL:
        return e["pubs"]
    rows = _rows(run(["channels", "members", "--channel", cid]), "members")
    if rows is None:  # mislukte fetch → eerdere leden behouden, venster verlengen
        if e:
            e["t"] = now
            return e["pubs"]
        _members[cid] = {"t": now, "pubs": set()}
        return set()
    pubs = {x.get("pubkey") for x in rows if x.get("pubkey")}  # geslaagd (evt. leeg)
    _members[cid] = {"t": now, "pubs": pubs}
    return pubs
