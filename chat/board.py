# SPDX-License-Identifier: EUPL-1.2
"""Het werk-overzicht serveren. Meer doet de chat hier niet.

De momentopname wordt gemaakt door `jobs/board.py` op de host waar de clones en
de sessies staan; dit leest alleen het bestand. Die scheiding is expres: de
chat-container heeft geen clones, geen `gh` en geen GitHub-toegang, en elke
traagheid daar zou anders een trage app worden.
"""
import json
import os
import time

import instellingen

PATH = instellingen.lees("BOARD_FILE", "/var/lib/ratatoskr/board.json")
# Boven deze leeftijd is de momentopname verdacht: de producent draait elke 10
# minuten, dus een half uur stilte betekent dat er iets stuk is. De app zegt dat
# dan — een leeg bord is anders niet te onderscheiden van een kapotte producent.
STALE_AFTER = 1800


def read(path=None):
    """(payload, http-status). Nooit een uitzondering naar buiten: een bord dat
    er niet is, is een nette 404 met wat je moet doen."""
    pad = path or PATH
    try:
        with open(pad) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"error": "no snapshot yet",
                "hint": "run jobs/board.py on the host that has the clones"}, 404
    except (OSError, ValueError) as e:
        return {"error": "snapshot unreadable: " + str(e)[:120]}, 500

    age = max(0.0, time.time() - float(data.get("generated_at") or 0))
    data["age_seconds"] = age
    data["stale_snapshot"] = age > STALE_AFTER
    return data, 200
