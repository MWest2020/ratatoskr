#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Work overview: collect what is running into one snapshot (board.json).

Three files: board_model.py is the pure core (column, age, staleness),
board_sources.py fetches (clones, GitHub, sessions), and this assembles and
writes. That split is not cosmetic: what the board SAYS must be testable without
GitHub, without a clock and without a disk.

Why a producer outside the chat: the data is not where the chat runs. OpenSpec
changes live in clones on this host, work sessions as run files in /tmp, PRs at
GitHub. The chat container is deliberately dependency-free and only serves the
file that comes out of here.

    python3 jobs/board.py > board.json     # or --out <path>

Everything that decides the column and the age is PURE (no I/O), so it can be
tested without GitHub or a clock: see jobs/test_board.py.
"""
import argparse
import json
import os
import time

import board_sources
import board_tmux
import yaml
from board_model import is_stale, summarise

HERE = os.path.dirname(os.path.abspath(__file__))
DAY = 86400.0


def load_config(path=None):
    return yaml.safe_load(open(path or os.path.join(HERE, "board.yml")))


def _merged_cached(src, now, cache_path, max_age):
    """Alleen de GEMERGEDE kant uit een cache.

    Die verandert alleen naar achteren, dus tien minuten oud is daar prima. De
    OPEN kant niet: die staat in de kolom waar iemand iets mee moet, en een
    gemergede PR die daar nog in staat vraagt om niets. Gemeten 2026-09-13: #125
    stond acht minuten na zijn merge nog in review, omdat beide kanten uit
    dezelfde cache van vlak vóór die merge kwamen.
    """
    try:
        cached = json.load(open(cache_path))
        if now - cached.get("at", 0) < max_age:
            return cached["rows"], []
    except (OSError, ValueError, KeyError):
        pass
    try:
        rows = board_sources.merged_prs(src["github_owner"], src.get("merged_days", 3), now)
    except Exception as e:
        try:
            return json.load(open(cache_path))["rows"], [f"merged PRs not refreshed: {e}"]
        except (OSError, ValueError, KeyError):
            return [], [f"merged PRs not fetched: {e}"]
    tmp = cache_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"at": now, "rows": rows}, f)
    os.replace(tmp, cache_path)
    return rows, []


def _pr_cards_cached(src, now, cache_path, max_age):
    """Open PR's vers, gemergede uit de cache."""
    errors = []
    try:
        open_rows = board_sources.open_prs(src["github_owner"])
    except Exception as e:
        # Geen verse open PR's? Dan liever niets tonen dan een oude lijst als
        # actueel presenteren — maar wel zeggen dat we het niet weten.
        open_rows, errors = [], [f"open PRs not fetched: {e}"]
    merged_rows, merged_errors = _merged_cached(src, now, cache_path, max_age)
    rows = open_rows + merged_rows
    return (board_sources.rows_to_cards(rows, now, set(src.get("ignore_repos") or ())),
            errors + merged_errors)


def build(cfg, now=None):
    """The snapshot. A source that fails comes along as `errors` — the board must
    be able to say 'I do not know' instead of 'there is nothing'."""
    now = now or time.time()
    src, cols = cfg["sources"], cfg["columns"]
    cards, errors = [], []
    cards += board_sources.openspec_cards(src["openspec_glob"], now)
    pr, pr_errors = _pr_cards_cached(src, now, src.get("pr_cache", "/tmp/board-prs.json"),
                                     src.get("pr_cache_seconds", 600))
    cards += pr
    errors += pr_errors
    try:
        cards += board_sources.session_cards(
            src["session_runs"], now, src.get("session_stale_seconds", 300))
    except Exception as e:
        errors.append(f"work sessions not read: {e}")
    # De tmux-sessies op deze host: waar het meeste werk feitelijk gebeurt en
    # wat tot 2026-09-16 alleen zichtbaar was voor wie aangekoppeld zat.
    #
    # Standaard UIT, anders niet: dit is de enige bron die de machine zelf
    # ondervraagt in plaats van een pad uit de config te lezen. Een producer die
    # ongevraagd `tmux` aanroept is niet te testen zonder tmux, en een bord dat
    # op de ene host andere kaarten toont dan op de andere hoort een keuze te
    # zijn die in de config staat.
    if src.get("tmux"):
        try:
            cards += board_tmux.tmux_cards(now, src.get("tmux_stale_seconds"))
        except Exception as e:
            errors.append(f"tmux sessions not read: {e}")
    for c in cards:
        c["stale"] = is_stale(c, cols)
    cards.sort(key=lambda c: (-c["stale"], -c["age_days"]))
    return {"generated_at": now, "columns": summarise(cards, cols),
            "cards": cards, "errors": errors}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="target file (written atomically)")
    ap.add_argument("--config")
    a = ap.parse_args()
    data = build(load_config(a.config))
    text = json.dumps(data, indent=1)
    if not a.out:
        print(text)
        return
    tmp = a.out + ".tmp"          # atomic: never serve half a file
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, a.out)
    print(f"[board] {len(data['cards'])} cards -> {a.out}"
          + (f" ({len(data['errors'])} read error(s))" if data["errors"] else ""))


if __name__ == "__main__":
    main()
