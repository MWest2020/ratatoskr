# SPDX-License-Identifier: EUPL-1.2
"""De poort van een werksessie: wie vraagt het, namens wie, en mag dat.

Apart van sessies.py omdat dit puur is — geen processen, geen bestanden — en
omdat beide bestanden anders over de 200 regels gaan.

Twee rollen per sessie, en dat onderscheid is de hele reden dat dit bestand
bestaat. De **starter** schreef de marker: odin in zijn antwoord, of de mens die
'm zelf typt. De **aanleiding** is de afzender van het bericht dat die beurt in
gang zette. Tot 2026-09-11 kende de listener alleen "wie schreef de marker", en
dan heet elke door odin gestarte sessie odin — terwijl de vraag van een mens kwam.
"""
import re

MARKER = re.compile(r"^[ \t]*!sessie[ \t]+([a-z0-9_-]+)[ \t]*(.*)$", re.M | re.I)


def lees_marker(tekst):
    """(type, opdracht) van de EERSTE `!sessie`-regel, of None. Alleen de eerste:
    één bericht zet hoogstens één sessie in gang."""
    m = MARKER.search(tekst or "")
    return (m.group(1).lower(), m.group(2).strip()) if m else None


def knip_marker(tekst):
    """De marker uit een te posten antwoord halen. Een geposte `!sessie`-regel zou
    later opnieuw gelezen kunnen worden; knippen maakt er een instructie van die
    precies één keer telt."""
    return MARKER.sub("", tekst or "", count=1).strip()


def types_voor(cfg, aanleiding):
    """Welke types deze aanleiding mag laten starten. Gebruikt door de clausule,
    zodat een agent geen sessie aankondigt die meteen een ⛔ krijgt."""
    return {n: t for n, t in ((cfg or {}).get("types") or {}).items()
            if aanleiding in (t.get("starters") or [])}


def mag_starten(cfg, typ, starter, aanleiding, lopend):
    """(ok, reden). Weigeren zonder reden bestaat niet: een stille weigering is
    niet te onderscheiden van een sessie die niets vond. De reden noemt WELKE
    voorwaarde faalde, anders staat de lezer voor een dichte deur zonder sleutel.

    De limiet gaat per AANLEIDING, niet per starter: met odin als tussenpersoon
    zou een limiet per starter de tweede persoon weigeren die odin iets vraagt.
    """
    types = (cfg or {}).get("types") or {}
    if typ not in types:
        namen = ", ".join(sorted(types)) or "(geen)"
        return False, f"onbekend sessietype '{typ}' — beschikbaar: {namen}"
    toegestaan = types[typ].get("starters") or []
    if starter not in toegestaan:
        return False, f"@{starter} mag het type '{typ}' niet starten"
    if aanleiding not in toegestaan:
        return False, (f"@{starter} mag geen sessie starten namens @{aanleiding} — "
                       f"die staat niet bij de starters van '{typ}'")
    if any(s["aanleiding"] == aanleiding for s in lopend):
        return False, f"er loopt al een sessie voor @{aanleiding} — die eerst afwachten"
    if len(lopend) >= int(cfg.get("max_gelijktijdig") or 2):
        return False, "er lopen al maximaal sessies — later opnieuw"
    return True, ""
