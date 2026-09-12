# SPDX-License-Identifier: EUPL-1.2
"""De poort van een werksessie: wie vraagt het, namens wie, en mag dat.

Apart van sessions.py omdat dit puur is — geen processen, geen bestanden — en
omdat beide bestanden anders over de 200 regels gaan.

Twee rollen per sessie, en dat onderscheid is de reden dat dit bestand bestaat.
De **starter** schreef de marker: odin in zijn antwoord, of de mens die 'm zelf
typt. De **requester** is de afzender van het bericht dat die beurt in gang
zette. Tot 2026-09-12 kende de listener alleen "wie schreef de marker", en dan
heet elke door odin gestarte sessie odin — terwijl de vraag van een mens kwam.

Engels, per ADR-0001. De omliggende modules zijn nog Nederlands; die gaan in één
mechanische change om.
"""
import re

MARKER = re.compile(r"^[ \t]*!sessie[ \t]+([a-z0-9_-]+)[ \t]*(.*)$", re.M | re.I)


def read_marker(text):
    """(type, task) van de EERSTE `!sessie`-regel, of None. Alleen de eerste:
    één bericht zet hoogstens één sessie in gang."""
    m = MARKER.search(text or "")
    return (m.group(1).lower(), m.group(2).strip()) if m else None


def strip_marker(text):
    """De marker uit een te posten antwoord halen. Een geposte `!sessie`-regel
    zou later opnieuw gelezen kunnen worden; knippen maakt er een instructie van
    die precies één keer telt."""
    return MARKER.sub("", text or "", count=1).strip()


def types_for(cfg, requester):
    """Welke types deze requester mag laten starten. De clausule gebruikt dit,
    zodat een agent geen sessie aankondigt die meteen een ⛔ krijgt."""
    return {n: t for n, t in ((cfg or {}).get("types") or {}).items()
            if requester in (t.get("starters") or [])}


def may_start(cfg, type_name, starter, requester, running):
    """(ok, reason). Weigeren zonder reden bestaat niet: een stille weigering is
    niet te onderscheiden van een sessie die niets vond. De reden noemt WELKE
    voorwaarde faalde, anders sta je voor een dichte deur zonder sleutel.

    De limiet gaat per REQUESTER, niet per starter: met odin als tussenpersoon
    zou een limiet per starter de tweede persoon weigeren die odin iets vraagt.
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
