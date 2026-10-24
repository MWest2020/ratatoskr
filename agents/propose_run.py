# SPDX-License-Identifier: MIT
"""What a finished propose session did, read from its run file: its cost, and
the writes inside its fence it was refused. Split from propose.py for the
line limit (2026-10-24)."""
import json
import os


def cost(job):
    """What the session cost, from its result line (0.0 when unknown)."""
    try:
        for ln in open(os.path.join(job["wt"], ".propose-run.jsonl")):
            if '"type":"result"' in ln.replace(" ", ""):
                return float(json.loads(ln).get("total_cost_usd") or 0)
    except (OSError, ValueError):
        pass
    return 0.0


def refused_writes(job):
    """Writes INSIDE the fence that the session was refused. They should never
    happen; on 2026-10-24 two amend sessions had every Edit refused, and the
    same run again worked. The wiring retries once when this is not empty."""
    fence = f"/openspec/changes/{job['change']}/"
    try:
        lines = open(os.path.join(job["wt"], ".propose-run.jsonl")).read().splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        if '"type":"result"' not in ln.replace(" ", ""):
            continue
        try:
            denials = json.loads(ln).get("permission_denials") or []
        except ValueError:
            continue
        out += [d["tool_input"].get("file_path", "") for d in denials
                if d.get("tool_name") in ("Edit", "Write")
                and fence in (d.get("tool_input") or {}).get("file_path", "")]
    return out
