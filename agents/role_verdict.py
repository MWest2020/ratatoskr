# SPDX-License-Identifier: MIT
"""What a habitat role said, read from its run output: the verdict JSON and its
findings. Split from build_runner.py for the line limit (2026-10-24)."""
import json
import os


def _verdict(text):
    """The first JSON object in a role's output that carries a verdict, where
    the key may come anywhere in it (2026-10-24: a reviewer put "summary"
    first, the parse found nothing, and its FAIL reached odin without a reason)."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            d = dec.raw_decode(text, i)[0]
        except ValueError:
            continue
        if isinstance(d, dict) and "verdict" in d:
            return d
    raise ValueError("no verdict")


def findings(store, limit=4):
    """The role's own findings, from the JSON verdict in its run output. A FAIL
    without them left odin unable to say why (2026-10-23: the reviewer found
    a missing docs update; the issue said only "verdict failed")."""
    try:
        name = next(f for f in os.listdir(store) if f.startswith("run-output-"))
        text = open(os.path.join(store, name)).read()
        d = _verdict(text)
    except (OSError, ValueError, TypeError, StopIteration):
        return []
    rows = sorted(d.get("findings") or [], key=lambda f: f.get("severity") != "blocking")
    if not rows:
        # the architect's verdict carries summary/risks/plan, not findings
        # (2026-10-24: its FAIL showed nothing, and odin asked Mark for the cause)
        short = lambda v: " ".join(str(v).split())[:600]  # noqa: E731
        return ([f"- [summary] {short(d['summary'])}"] if d.get("summary") else []) + \
            [f"- [risk] {short(r)}" for r in (d.get("risks") or [])[:limit - 1]]
    return [f"- [{f.get('severity', '?')}] {f.get('location', '')}: "
            f"{' '.join(str(f.get('description', '')).split())[:600]}" for f in rows[:limit]]
