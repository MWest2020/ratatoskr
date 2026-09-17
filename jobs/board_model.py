#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The pure core of the work overview: column, age, staleness, summary.

Separate from board.py and board_sources.py so this is testable without GitHub,
without a clock and without a disk — and so those two need not import each other
(which gave a circular import).

This is what the board SAYS. The rest only fetches and writes.
"""
DAY = 86400.0


def pr_column(pr):
    """Which column does this PR belong in?

    A draft is work in progress. An OPEN, non-draft PR waits on a human by
    definition: in this flow it stays put until someone merges it. Merged is the
    exit.

    Why not on `reviewDecision`: `gh search prs` does not know that field
    (measured 2026-09-12: "Unknown JSON field"). Fetching it per repo with `gh pr
    list` would cost one call per repo for a nuance that adds nothing here — open
    and non-draft IS waiting for review here.
    """
    if pr.get("merged"):
        return "merged"
    return "building" if pr.get("draft") else "review"


def age_days(since, now):
    """How many days has this been here (never negative — a clock running behind
    must not produce a card 'from the future')."""
    return max(0.0, (now - float(since or now)) / DAY)


def is_stale(card, columns):
    """Has this card been in its column longer than the threshold? `stale_days: 0`
    means 'never stale' — that is the exit column, anything may rest there."""
    threshold = next((c.get("stale_days", 0) for c in columns if c["key"] == card["column"]), 0)
    return bool(threshold) and card["age_days"] > threshold


def summarise(cards, columns):
    """Per column: how many cards, how many of them stale. The board shows this at
    the top so that 'nothing is stuck' is a visible outcome too."""
    out = []
    for c in columns:
        inside = [k for k in cards if k["column"] == c["key"]]
        out.append({"key": c["key"], "title": c["title"],
                    "count": len(inside),
                    "stale": sum(1 for k in inside if k["stale"])})
    return out
