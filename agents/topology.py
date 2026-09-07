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
# 'welcome-everyone'/'Welcome'); die horen niet in de poll-set. Spiegelt (bewust
# gedupliceerd, andere dir/geen gedeelde import) de HIDE in chat/buzzcli.py. De
# PREFER-map daar hoeven we niet te kopiëren ZOLANG channels.yml de canonieke cids
# bevat: die wint bij naam-botsing ({**live, **fallback}). Ontbreekt een naam in
# channels.yml, dan valt 'ie terug op de eerste relay-record voor die naam.
_HIDE = {"welcome-everyone", "Welcome"}

_channels = {"t": 0.0, "data": None}
_members = {}  # cid -> {"t": float, "pubs": set}


def _rows(out, key):
    """JSON-lijst uit relay-output: kale lijst of {<key>: [...]}. None bij onparse-
    baar OF een onverwacht type (null/string/getal) — dan mag de aanroeper niet
    crashen op .get(); die None is 'mislukte fetch'."""
    try:
        d = json.loads(out)
    except Exception:
        return None
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        v = d.get(key)  # afwezig (bv. {"error":..}) OF geen lijst ({..}/"x") = mislukt
        return v if isinstance(v, list) else None
    return None


def poll_channels(run, fallback, now=None):
    """{name: cid} = channels.yml (`fallback`, gecureerd + autoritair op cid) plus
    de echt-nieuwe namen uit de live relay-lijst. Junk-kanalen (`_HIDE`) eruit. Een
    mislukte/lege fetch overschrijft een eerder geslaagde cache NIET (val terug op
    die cache; alleen zonder cache op de kale fallback)."""
    now = time.time() if now is None else now
    if _channels["data"] is not None and now - _channels["t"] < TTL:
        return _channels["data"]
    rows = _rows(run(["channels", "list"]), "channels")
    if not rows:  # mislukt (None) OF leeg — een lege kanaallijst is nooit legitiem
        if _channels["data"] is not None:
            _channels["t"] = now          # goede cache behouden + venster verlengen
            return _channels["data"]
        return dict(fallback)             # eerste mislukking: NIET cachen (net als
                                          # members) → volgende tick probeert opnieuw
    live = {}
    for x in rows:
        name, cid = x.get("name"), (x.get("channel_id") or x.get("id"))
        if name and cid and name not in _HIDE:
            live.setdefault(name, cid)  # dedup: eerste record per naam
    # Dedup op NAAM én CID: channels.yml (canoniek) eerst, dan de nieuwe relay-namen.
    # Zo staat een kanaal dat onder twee namen dezelfde cid heeft maar één keer in de
    # poll-set (anders zou de listener 't dubbel pollen).
    out, seen_cids = {}, set()
    for name, cid in list(fallback.items()) + list(live.items()):
        if name in out or cid in seen_cids:
            continue
        out[name] = cid
        seen_cids.add(cid)
    _channels.update(t=now, data=out)
    return out


def members(run, cid, now=None):
    """set van member-pubkeys van een kanaal (relay), ~TTL gecachet. Onderscheidt
    een MISLUKTE fetch (`None` → goede cache behouden) van een echt LEEG kanaal
    (`[]` → dat cachen, zodat 'laatste lid weg' ook doorwerkt)."""
    now = time.time() if now is None else now
    e = _members.get(cid)
    if e and now - e["t"] < TTL:
        return e["pubs"]
    rows = _rows(run(["channels", "members", "--channel", cid]), "members")
    if rows is None:  # mislukte fetch → eerdere leden behouden; GEEN lege entry
        if e:                          # cachen zonder eerdere entry (dat zou een
            e["t"] = now               # echt-leeg kanaal nabootsen en 60s vastzetten)
            return e["pubs"]
        return set()
    pubs = {x.get("pubkey") for x in rows if x.get("pubkey")}  # geslaagd (evt. leeg)
    _members[cid] = {"t": now, "pubs": pubs}
    return pubs


def is_scoped(def_channels, cname, agent_pub, member_pubs_fn):
    """Reageert een agent in dit kanaal? Handbook-scope OF relay-lid (union). Puur
    (geen I/O) zodat de kernregel getest kan worden. `member_pubs_fn` is een 0-arg
    callable — LUI: alleen aangeroepen als de handbook-scope de vraag niet al
    beantwoordt, zodat we geen members-fetch doen voor een def-gescopt kanaal."""
    return cname in def_channels or agent_pub in member_pubs_fn()


# Kanalen waar ELKE agent in post, ongeacht zijn eigen scope: de statistiekregel
# per beurt en de limitatie-melding. Zonder lidmaatschap faalt die send, en wel
# stil — alleen zichtbaar in het listener-log. Waargenomen 2026-09-07: odin zat
# niet in #statistics en vijf agents niet in #escalatie, dus de escalatieketen
# waar Mark om vroeg was in de praktijk dood.
REPORT_CHANNELS = ("statistics", "escalatie")


def missing_memberships(agents, channels, name2pub, member_pubs_fn):
    """[(handle, kanaalnaam)] voor elk kanaal waar een agent in post maar geen lid
    van is. Puur op de meegegeven lookups, zodat het testbaar is zonder relay."""
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
