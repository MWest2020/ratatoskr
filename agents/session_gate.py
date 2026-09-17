# SPDX-License-Identifier: MIT
"""The gate of a work session: who asks, on whose behalf, and is that allowed.

Separate from sessions.py because this is pure — no processes, no files — and
because otherwise both files would go over 200 lines.

Two roles per session, and that distinction is why this file exists. The
**starter** wrote the marker: odin in his answer, or the human typing it
themselves. The **requester** is the sender of the message that set the turn in
motion. Until 2026-09-12 the listener only knew "who wrote the marker", and then
every session odin starts is called odin — while the question came from a human.
"""
import re

MARKER = re.compile(r"^[ \t]*!sessie[ \t]+([a-z0-9_-]+)[ \t]*(.*)$", re.M | re.I)


def read_marker(text):
    """(type, task) of the FIRST `!sessie` line, or None. Only the first: one
    message sets at most one session in motion."""
    m = MARKER.search(text or "")
    return (m.group(1).lower(), m.group(2).strip()) if m else None


def strip_marker(text):
    """Strip the marker out of an answer before posting it. A posted `!sessie`
    line could be read again later; stripping makes it an instruction that
    counts exactly once."""
    return MARKER.sub("", text or "", count=1).strip()


def types_for(cfg, requester):
    """Which types this requester may have started. The clause uses this, so an
    agent does not announce a session that gets an immediate ⛔."""
    return {n: t for n, t in ((cfg or {}).get("types") or {}).items()
            if requester in (t.get("starters") or [])}


def may_start(cfg, type_name, starter, requester, running):
    """(ok, reason). Refusing without a reason does not exist: a silent refusal
    is indistinguishable from a session that found nothing. The reason names
    WHICH condition failed, otherwise you face a locked door without a key.

    The limit is per REQUESTER, not per starter: with odin as intermediary a
    per-starter limit would refuse the second person who asks odin something.
    """
    types = (cfg or {}).get("types") or {}
    if type_name not in types:
        names = ", ".join(sorted(types)) or "(geen)"
        return False, f"onbekend sessietype '{type_name}' — beschikbaar: {names}"
    allowed = types[type_name].get("starters") or []
    if starter not in allowed:
        return False, f"@{starter} mag het type '{type_name}' niet starten"
    if requester not in allowed:
        return False, (f"@{starter} mag geen sessie starten namens @{requester} — "
                       f"die staat niet bij de starters van '{type_name}'")
    if any(s["requester"] == requester for s in running):
        return False, f"er loopt al een sessie voor @{requester} — die eerst afwachten"
    if len(running) >= int(cfg.get("max_concurrent") or 2):
        return False, "er lopen al maximaal sessies — later opnieuw"
    return True, ""
