#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
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
import yaml
from board_model import is_stale, summarise

HERE = os.path.dirname(os.path.abspath(__file__))
DAY = 86400.0


def load_config(path=None):
    return yaml.safe_load(open(path or os.path.join(HERE, "board.yml")))


def _pr_cards_cached(src, now, cache_path, max_age):
    """PRs come from GitHub and change slowly; sessions change every minute.
    Caching the PR side lets the snapshot run often without querying GitHub every
    time — and that is what makes a RUNNING session visible."""
    try:
        cached = json.load(open(cache_path))
        if now - cached.get("at", 0) < max_age:
            return cached["cards"], []
    except (OSError, ValueError, KeyError):
        pass
    try:
        cards = board_sources.pr_cards(src["github_owner"], src.get("merged_days", 3),
                                       now, set(src.get("ignore_repos") or ()))
    except Exception as e:
        # No fresh PRs? Fall back on the cache, however old — but say so.
        try:
            return json.load(open(cache_path))["cards"], [f"PRs not refreshed: {e}"]
        except (OSError, ValueError, KeyError):
            return [], [f"PRs not fetched: {e}"]
    tmp = cache_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"at": now, "cards": cards}, f)
    os.replace(tmp, cache_path)
    return cards, []


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
        cards += board_sources.session_cards(src["session_runs"], now)
    except Exception as e:
        errors.append(f"work sessions not read: {e}")
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
