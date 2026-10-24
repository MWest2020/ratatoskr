#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarise agents/activity.py's log: who ran, on what, with which tools.

    python3 scripts/activity_report.py [--json out.json]

Prints a short text summary; `--json` writes the full summary (per agent,
model, project, kind, billing, tool and skill) for a dashboard.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agents"))
import activity  # noqa: E402

MODEL_NAMES = {"sonnet": "Sonnet", "opus": "Opus", "haiku": "Haiku", "default": "default",
               "fable": "Fable"}


def model_family(m):
    m = (m or "").lower()
    for k, v in MODEL_NAMES.items():
        if k in m:
            return v
    return m or "unknown"


def summary(rows):
    by = defaultdict(lambda: {"runs": 0, "cost": 0.0, "turns": 0})
    agents = defaultdict(lambda: {"runs": 0, "cost": 0.0, "models": Counter(), "kinds": Counter(),
                                  "tools": Counter(), "skills": Counter(), "projects": Counter()})
    tools, skills, models, projects, kinds, billing = (Counter() for _ in range(6))
    first, last = None, None
    for r in rows:
        a = agents[r["agent"]]
        fam = model_family(r.get("model"))
        a["runs"] += 1
        a["cost"] += r.get("cost") or 0
        a["models"][fam] += 1
        a["kinds"][r["kind"]] += 1
        a["projects"][r.get("project") or "?"] += 1
        for t, n in (r.get("tools") or {}).items():
            a["tools"][t] += n
            tools[t] += n
        for s in (r.get("skills_used") or []) + (r.get("skills") or []):
            a["skills"][s] += 1
            skills[s] += 1
        models[fam] += 1
        projects[r.get("project") or "?"] += 1
        kinds[r["kind"]] += 1
        billing[r.get("billing", "?")] += r.get("cost") or 0
        for key in (("model", fam), ("project", r.get("project") or "?"), ("kind", r["kind"])):
            by[key]["runs"] += 1
            by[key]["cost"] += r.get("cost") or 0
            by[key]["turns"] += r.get("turns") or 0
        first = min(first or r["ts"], r["ts"])
        last = max(last or r["ts"], r["ts"])
    return {
        "runs": len(rows), "cost": round(sum(r.get("cost") or 0 for r in rows), 2),
        "first": first, "last": last,
        "agents": {k: {"runs": v["runs"], "cost": round(v["cost"], 2),
                       "models": dict(v["models"]), "kinds": dict(v["kinds"]),
                       "tools": dict(v["tools"].most_common(12)),
                       "skills": dict(v["skills"]), "projects": dict(v["projects"])}
                   for k, v in sorted(agents.items(), key=lambda kv: -kv[1]["runs"])},
        "models": dict(models), "projects": dict(projects), "kinds": dict(kinds),
        "tools": dict(tools.most_common(20)), "skills": dict(skills),
        "billing_cost": {k: round(v, 2) for k, v in billing.items()},
        "by": {f"{k[0]}:{k[1]}": {"runs": v["runs"], "cost": round(v["cost"], 2),
                                  "turns": v["turns"]} for k, v in by.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = []
    try:
        for ln in open(activity.LOG):
            try:
                rows.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    s = summary(rows)
    print(f"{s['runs']} runs, ${s['cost']:.2f}; models {s['models']}; kinds {s['kinds']}")
    for name, a_ in list(s["agents"].items())[:12]:
        print(f"  {name}: {a_['runs']} runs, ${a_['cost']:.2f}, models {a_['models']}, "
              f"top tools {list(a_['tools'])[:4]}")
    if a.json:
        json.dump(s, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
