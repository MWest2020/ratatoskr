#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Werk-overzicht: verzamel wat er loopt tot één momentopname (board.json).

Drie bestanden: board_model.py is de pure kern (kolom, ouderdom, muf),
board_sources.py haalt op (clones, GitHub, sessies), en dit stelt samen en
schrijft weg. Die scheiding is niet cosmetisch: wat het bord zégt moet te testen
zijn zonder GitHub, zonder klok en zonder schijf.

Waarom een producent buiten de chat: de gegevens liggen niet waar de chat draait.
OpenSpec-changes staan in clones op deze host, werksessies als runbestanden in
/tmp, PR's bij GitHub. De chat-container is expres dependency-loos en serveert
alleen het bestand dat hier uit komt.

    python3 jobs/board.py > board.json     # of --out <pad>

Alles wat de kolom en de ouderdom bepaalt is PUUR (geen I/O), zodat het te
testen is zonder GitHub of een klok: zie jobs/test_board.py.
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


def build(cfg, now=None):
    """De momentopname. Een bron die faalt komt als `errors` mee — het bord moet
    kunnen zeggen 'ik weet het niet' in plaats van 'er is niets'."""
    now = now or time.time()
    src, cols = cfg["sources"], cfg["columns"]
    cards, errors = [], []
    cards += board_sources.openspec_cards(src["openspec_glob"], now)
    try:
        cards += board_sources.pr_cards(src["github_owner"], src.get("merged_days", 3),
                                        now, set(src.get("ignore_repos") or ()))
    except Exception as e:
        errors.append(f"PR's niet opgehaald: {e}")
    try:
        cards += board_sources.session_cards(src["session_runs"], now)
    except Exception as e:
        errors.append(f"werksessies niet gelezen: {e}")
    for c in cards:
        c["stale"] = is_stale(c, cols)
    cards.sort(key=lambda c: (-c["stale"], -c["age_days"]))
    return {"generated_at": now, "columns": summarise(cards, cols),
            "cards": cards, "errors": errors}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="doelbestand (atomisch geschreven)")
    ap.add_argument("--config")
    a = ap.parse_args()
    data = build(load_config(a.config))
    tekst = json.dumps(data, indent=1)
    if not a.out:
        print(tekst)
        return
    tmp = a.out + ".tmp"          # atomisch: nooit een half bestand serveren
    with open(tmp, "w") as f:
        f.write(tekst)
    os.replace(tmp, a.out)
    print(f"[board] {len(data['cards'])} kaarten -> {a.out}"
          + (f" ({len(data['errors'])} leesfout(en))" if data["errors"] else ""))


if __name__ == "__main__":
    main()
