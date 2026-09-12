# SPDX-License-Identifier: EUPL-1.2
"""Serve the work overview. That is all the chat does here.

The snapshot is produced by `jobs/board.py` on the host that has the clones and
the sessions; this only reads the file. That split is deliberate: the chat
container has no clones, no `gh` and no GitHub access, and any slowness there
would otherwise become a slow app.
"""
import json
import os
import time

import settings

PATH = settings.read("BOARD_FILE", "/var/lib/ratatoskr/board.json")
# Above this age the snapshot is suspect: the producer runs every 10 minutes, so
# half an hour of silence means something is broken. The app says so then — an
# empty board is otherwise indistinguishable from a broken producer.
STALE_AFTER = 1800


def read(path=None):
    """(payload, http status). Never an exception to the outside: a board that is
    not there is a clean 404 with what to do about it."""
    target = path or PATH
    try:
        with open(target) as f:
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
