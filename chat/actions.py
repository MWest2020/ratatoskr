# SPDX-License-Identifier: EUPL-1.2
"""Agent/kanaal-acties voor de chat-backend, apart van server.py (routing) zodat
beide onder de =<200-regel-conventie blijven. Elke functie geeft (status, payload).
"""
import json
import re
import sys

import roster
from buzzcli import ADMIN_OFF, buzz, buzz_admin, channel_member_pubkeys, valid_cid

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")
_MENTION_ERR = re.compile(r"mention '@([A-Za-z0-9_-]+)' does not match")


def _a_member_of(cid):
    """Een pubkey die écht LID is van DIT kanaal (anker voor de force-mention).
    Deterministisch (gesorteerd) en bij voorkeur een NIET-agent-lid, zodat het
    anker sowieso niet met een agent te verwarren is. Het lid wordt niet ge-@t in
    de content, dus de listener (die op @handle in de tekst triggert) reageert er
    niet op; de voorkeur is een extra gordel."""
    members = sorted(p for p in channel_member_pubkeys(cid) if p)  # stabiel per call
    if not members:
        return None
    agents = {a["pubkey"] for a in roster.chat_agents()}
    return next((p for p in members if p not in agents), members[0])


def add_agent(cid, name):
    """Voeg een agent (naam→pubkey uit de registry) als bot toe."""
    if not valid_cid(cid):
        return 400, {"error": "onbekend kanaal"}
    pk = roster.agent_pubkey(name)
    if not pk:
        return 404, {"error": f"'{name}' is geen agent (sessies/mark voeg je niet zo toe)"}
    rc, out, err = buzz_admin(["channels", "add-member", "--channel", cid,
                               "--pubkey", pk, "--role", "bot"])
    if rc is None:
        return 503, {"error": ADMIN_OFF}
    if rc != 0:
        return 502, {"error": (err or out).strip()[:200]}
    return 200, {"ok": True, "name": name}


def send(cid, content, force=False):
    """Verstuur een bericht. Zonder --mention resolvet de relay een @agent naar het
    lid en triggert 'm; een @naam die geen lid is geeft een 409 met een keuze
    (toevoegen als 't een agent is, of 'toch versturen'). Met `force` geven we een
    écht bestaand kanaal-lid (`_a_member_of`) als anker-mention mee zodat álle
    @woorden presentation-only worden — voor @here, een geplakte handle, e.d."""
    if not valid_cid(cid):
        return 400, {"error": "onbekend kanaal"}
    content = (content or "").strip()
    if not content:
        return 400, {"error": "leeg bericht"}
    args = ["messages", "send", "--channel", cid, "--content", "-"]
    if force:
        anchor = _a_member_of(cid)
        if anchor:
            args += ["--mention", anchor]  # echt lid → maakt @woorden presentation-only
    rc, out, err = buzz(args, stdin=content)
    if rc == 0:
        return 200, {"ok": True}
    m = _MENTION_ERR.search((err or "") + (out or ""))
    if m:
        who = m.group(1)
        return 409, {
            "missing_agent": who,
            "known": roster.agent_pubkey(who) is not None,  # alleen échte agents → toevoegen
            "can_force": True,                              # 'toch versturen' (presentation-only) mag
            "channel": cid,
        }
    return 502, {"error": (err or out or "").strip()[:200]}


def _add_hub(create_out):
    """Best-effort: de hub-agent als lid van een net-gemaakt kanaal. Mag NOOIT
    raisen — het kanaal bestaat al. Faalt stil-maar-zichtbaar (log naar stderr,
    return None/False), zodat een add-fout niet de hele create doet omvallen.

    De hub wordt op ROL opgezocht (`meta-agent`), niet op naam: na de hernoeming
    coordinator -> odin gaf de naam-variant `geen cid/pubkey` en kwam er in geen
    enkel nieuw kanaal nog een hub te zitten."""
    try:
        d = json.loads(create_out)
        cid = d.get("channel_id") or d.get("id")  # relay gebruikt beide
        co = roster.hub_pubkey()
        if not (cid and co):
            sys.stderr.write("[create] hub-add overgeslagen: geen cid/hub-pubkey\n")
            return False
        ar, _o, ae = buzz_admin(["channels", "add-member", "--channel", cid,
                                 "--pubkey", co, "--role", "bot"])
        if ar is None or ar != 0:
            sys.stderr.write(f"[create] hub-add faalde: {(ae or _o).strip()[:120]}\n")
        return ar == 0
    except Exception as e:  # noqa: BLE001 — create is al geslaagd; add is bijzaak
        sys.stderr.write(f"[create] hub-add fout: {e}\n")
        return False


def create_channel(name):
    """Maak een open kanaal + voeg de hub-agent standaard toe (best-effort:
    mislukt de add, dan bestaat het kanaal nog steeds; `hub_added` meldt 't)."""
    name = (name or "").strip().lower()
    if not _NAME_RE.match(name):
        return 400, {"error": "naam: a-z 0-9 _ - (max 31)"}
    rc, out, err = buzz_admin(["channels", "create", "--name", name,
                               "--type", "stream", "--visibility", "open"])
    if rc is None:
        return 503, {"error": ADMIN_OFF}
    if rc != 0:
        return 502, {"error": err.strip()[:200]}
    return 200, {"ok": True, "name": name, "hub_added": _add_hub(out)}
