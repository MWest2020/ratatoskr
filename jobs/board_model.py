#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""De pure kern van het werk-overzicht: kolom, ouderdom, muf, samenvatting.

Apart van board.py en board_sources.py zodat dit te testen is zonder GitHub,
zonder klok en zonder schijf — en zodat die twee elkaar niet hoeven te
importeren (dat gaf een circulaire import).

Hier staat wat het bord zégt. De rest haalt alleen op en schrijft weg.
"""
DAY = 86400.0


def pr_column(pr):
    """In welke kolom hoort deze PR?

    Een draft is werk in uitvoering. Een OPEN, niet-draft PR wacht per definitie
    op een mens: in deze flow blijft hij staan tot iemand 'm merget. Gemerged is
    de uitgang.

    Waarom niet op `reviewDecision`: `gh search prs` kent dat veld niet (gemeten
    2026-09-12: "Unknown JSON field"). Dat per repo ophalen met `gh pr list` zou
    een aanroep per repo kosten voor een nuance die hier niets toevoegt — open
    en niet-draft ís hier wachten op review.
    """
    if pr.get("merged"):
        return "merged"
    return "building" if pr.get("draft") else "review"


def age_days(since, now):
    """Hoeveel dagen staat dit er al (nooit negatief — een klok die achterloopt
    mag geen kaart 'uit de toekomst' opleveren)."""
    return max(0.0, (now - float(since or now)) / DAY)


def is_stale(card, columns):
    """Staat deze kaart langer in zijn kolom dan de drempel? `stale_days: 0`
    betekent 'nooit muf' — dat is de uitgangskolom, daar mag alles liggen."""
    drempel = next((c.get("stale_days", 0) for c in columns if c["key"] == card["column"]), 0)
    return bool(drempel) and card["age_days"] > drempel


def summarise(cards, columns):
    """Per kolom: hoeveel kaarten, hoeveel daarvan muf. Het bord toont dit bovenaan
    zodat 'niets loopt vast' óók een zichtbare uitkomst is."""
    out = []
    for c in columns:
        inside = [k for k in cards if k["column"] == c["key"]]
        out.append({"key": c["key"], "title": c["title"],
                    "count": len(inside),
                    "stale": sum(1 for k in inside if k["stale"])})
    return out
