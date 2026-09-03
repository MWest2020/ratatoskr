# SPDX-License-Identifier: EUPL-1.2
"""Agent/kanaal-acties voor de chat-backend, apart van server.py (routing) zodat
beide onder de =<200-regel-conventie blijven. Elke functie geeft (status, payload).
"""
import json
import re

import roster
from buzzcli import buzz, valid_cid

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")
_MENTION_ERR = re.compile(r"mention '@([A-Za-z0-9_-]+)' does not match")


def _coordinator():
    return roster.agent_pubkey("coordinator")


def add_agent(cid, name):
    """Voeg een agent (naam→pubkey uit de registry) als bot toe."""
    if not valid_cid(cid):
        return 400, {"error": "onbekend kanaal"}
    pk = roster.agent_pubkey(name)
    if not pk:
        return 404, {"error": f"'{name}' is geen agent (sessies/mark voeg je niet zo toe)"}
    rc, out, err = buzz(["channels", "add-member", "--channel", cid,
                         "--pubkey", pk, "--role", "bot"])
    if rc != 0:
        return 502, {"error": (err or out).strip()[:200]}
    return 200, {"ok": True, "name": name}


def send(cid, content, force=False):
    """Verstuur een bericht. Zonder --mention resolvet de relay een @agent naar het
    lid en triggert 'm; een @naam die geen lid is geeft een 409 met een keuze
    (toevoegen als 't een agent is, of 'toch versturen'). Met `force` geven we een
    lid-mention (coordinator, zit in elk kanaal) mee zodat álle @woorden
    presentation-only worden — voor @here, een geplakte handle, e.d."""
    if not valid_cid(cid):
        return 400, {"error": "onbekend kanaal"}
    content = (content or "").strip()
    if not content:
        return 400, {"error": "leeg bericht"}
    args = ["messages", "send", "--channel", cid, "--content", "-"]
    if force:
        co = _coordinator()
        if co:
            args += ["--mention", co]  # lid → maakt @woorden presentation-only
    rc, out, err = buzz(args, stdin=content)
    if rc == 0:
        return 200, {"ok": True}
    m = _MENTION_ERR.search(err or "")
    if m:
        who = m.group(1)
        return 409, {
            "missing_agent": who,
            "known": roster.agent_pubkey(who) is not None,  # alleen échte agents → toevoegen
            "can_force": True,                              # 'toch versturen' (presentation-only) mag
            "channel": cid,
        }
    return 502, {"error": (err or "").strip()[:200]}


def create_channel(name):
    """Maak een open kanaal + voeg coordinator standaard toe (best-effort:
    mislukt de add, dan bestaat het kanaal nog steeds)."""
    name = (name or "").strip().lower()
    if not _NAME_RE.match(name):
        return 400, {"error": "naam: a-z 0-9 _ - (max 31)"}
    rc, out, err = buzz(["channels", "create", "--name", name,
                         "--type", "stream", "--visibility", "open"])
    if rc != 0:
        return 502, {"error": err.strip()[:200]}
    added = None
    try:
        d = json.loads(out)
        new_cid = d.get("channel_id") or d.get("id")  # relay gebruikt beide
        co = _coordinator()
        if new_cid and co:
            ar, _o, ae = buzz(["channels", "add-member", "--channel", new_cid,
                               "--pubkey", co, "--role", "bot"])
            added = (ar == 0)
    except (ValueError, AttributeError):
        pass
    return 200, {"ok": True, "name": name, "coordinator_added": added}
