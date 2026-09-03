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
    """{name: cid} van alle open kanalen (relay), met `fallback` (channels.yml)
    als vangnet. Union bij succes zodat een bekend kanaal niet wegvalt als de
    relay 't (even) niet teruggeeft."""
    now = time.time() if now is None else now
    if _channels["data"] is not None and now - _channels["t"] < TTL:
        return _channels["data"]
    rows = _rows(run(["channels", "list"]), "channels")
    data = None
    if rows is not None:
        data = {x.get("name"): (x.get("channel_id") or x.get("id"))
                for x in rows if x.get("name") and (x.get("channel_id") or x.get("id"))}
    merged = {**fallback, **data} if data else dict(fallback)  # fout/leeg → alleen vangnet
    _channels.update(t=now, data=merged)
    return merged


def members(run, cid, now=None):
    """set van member-pubkeys van een kanaal (relay), ~TTL gecachet. Een lege
    fetch wordt alleen gecachet als we nog niets beters hadden."""
    now = time.time() if now is None else now
    e = _members.get(cid)
    if e and now - e["t"] < TTL:
        return e["pubs"]
    rows = _rows(run(["channels", "members", "--channel", cid]), "members")
    pubs = {x.get("pubkey") for x in rows if x.get("pubkey")} if rows else set()
    if pubs or not (e and e["pubs"]):  # geen goede cache overschrijven met leeg
        _members[cid] = {"t": now, "pubs": pubs}
        return pubs
    e["t"] = now  # behoud vorige leden, verleng het venster
    return e["pubs"]
