# SPDX-License-Identifier: MIT
"""Which agent ran, on which model, with which skills and tools, for what.

Mark, 2026-10-24: "can we track also which agents used with models and skills
and tools? I prob need this for a linkedin post." One JSONL line per run in
`~/.local/state/ratatoskr/activity.jsonl`, written where each kind of run
ends:

    kind      chat (a listener turn), propose (a writing session), habitat (a role)
    agent     the handle, or the habitat role
    project   the repository, or for chat the channel's project
    model     what ran (for chat: the model with the most tokens)
    skills    the skills the agent declared, and those it loaded (Skill tool)
    tools     {tool name: calls} as far as the run reports them
    cost, turns, billing (api | subscription)

`scripts/activity_backfill.py` fills the history from what already exists;
`scripts/activity_report.py` summarises it.
"""
import json
import os
import time
from collections import Counter

LOG = os.path.expanduser("~/.local/state/ratatoskr/activity.jsonl")
_on = {"live": False}


def enable():
    """The listener turns the live log on; tests never do, so a test turn
    never lands in the real log (2026-10-24: the first suite run did)."""
    _on["live"] = True


def tools_from_stream(lines):
    """({tool: calls}, [skills loaded]) from stream-json lines."""
    tools, skills = Counter(), []
    for ln in lines:
        try:
            ev = json.loads(ln)
        except (ValueError, TypeError):
            continue
        msg = ev.get("message") if isinstance(ev, dict) else None
        content = msg.get("content") if isinstance(msg, dict) else None
        for c in content if isinstance(content, list) else []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                tools[c.get("name") or "?"] += 1
                if c.get("name") == "Skill":
                    skills.append(str((c.get("input") or {}).get("skill") or "?"))
    return dict(tools), skills


def model_from_stream(lines):
    for ln in lines:
        try:
            ev = json.loads(ln)
        except (ValueError, TypeError):
            continue
        if isinstance(ev, dict) and ev.get("type") == "system" and ev.get("subtype") == "init":
            return ev.get("model") or ""
    return ""


def record(kind, agent, project, model="", skills=None, skills_used=None, tools=None,
           cost=0.0, turns=0, billing="subscription", ref="", ts=None, log=LOG):
    """Append one run. Never raises: tracking must not break the work. The
    default log is written only once the listener enabled it; an explicit
    `log` (the backfill, the tests) always is."""
    if log == LOG and not _on["live"]:
        return
    try:
        row = {"ts": int(ts if ts is not None else time.time()), "kind": kind,
               "agent": agent, "project": project, "model": model or "",
               "skills": sorted(set(skills or [])), "skills_used": sorted(set(skills_used or [])),
               "tools": dict(tools or {}), "cost": round(float(cost or 0), 4),
               "turns": int(turns or 0), "billing": billing, "ref": ref}
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except (OSError, TypeError, ValueError):
        pass


def record_propose(job, billing="subscription", log=LOG):
    """A finished propose session, from its run file."""
    try:
        lines = open(os.path.join(job["wt"], ".propose-run.jsonl")).read().splitlines()
    except (OSError, KeyError):
        lines = []
    tools, used = tools_from_stream(lines)
    cost = 0.0
    for ln in lines:
        if '"type":"result"' in ln.replace(" ", ""):
            try:
                cost = float(json.loads(ln).get("total_cost_usd") or 0)
            except ValueError:
                pass
    record("propose", "propose-session", job.get("repo", ""), model=model_from_stream(lines),
           skills_used=used, tools=tools, cost=cost, billing=billing,
           ref=job.get("change", ""), log=log)
