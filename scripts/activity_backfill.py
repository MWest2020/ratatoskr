#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fill agents/activity.py's log with the runs from before it existed.

    python3 scripts/activity_backfill.py [--before <epoch>] [--dry-run]

Sources, each read-only:
- habitat roles: every run-report.json under the habitat run-logs; the model
  from the role's job log (it names the same run id);
- propose sessions: every ~/.worktrees/propose/*/.propose-run.jsonl;
- chat turns: the #statistics history ("handle · #channel · model · N turns ·
  $x"), which has no tool counts.

Rows get `ref: backfill:<source>`. Only runs before `--before` (default: now)
are written, so a run the live hooks already logged is not counted twice.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agents"))
import activity  # noqa: E402

HABITAT = os.path.expanduser("~/.local/state/habitat/run-logs")
PROPOSE = os.path.expanduser("~/.worktrees/propose")
API_REPOS = {"convergence"}
STAT = re.compile(r"^(\S+) · #(\S+) · (.+?) · (\d+) turns · \$([0-9.]+)")


def habitat_rows():
    models = {}
    for log in glob.glob(os.path.join(HABITAT, "*.log")):
        text = open(log, errors="replace").read()
        m, r = re.search(r"model uit rolbestand: (\S+)", text), re.search(
            r"run-report-(\d{8}-\d{6}-\d+)\.html", text)
        if r:
            models[r.group(1)] = m.group(1) if m else "default"
    for rep in glob.glob(os.path.join(HABITAT, "artifacts", "*", "*", "run-report.json")):
        try:
            d = json.load(open(rep))
        except (OSError, ValueError):
            continue
        repo = d.get("repo", "").rstrip("/").split("/")[-1].removesuffix(".git")
        ts = time.mktime(time.strptime(d.get("finished_at", "1970-01-01T00:00:00Z")[:19],
                                       "%Y-%m-%dT%H:%M:%S")) - time.timezone
        yield dict(kind="habitat", agent=d.get("role", "?"), project=repo,
                   model=models.get(d.get("run_id"), "default"), cost=d.get("total_cost_usd"),
                   turns=d.get("num_turns"), billing="api" if repo in API_REPOS else "subscription",
                   ref=f"backfill:habitat:{d.get('change')}:{d.get('verdict')}", ts=ts)


def propose_rows():
    for run in glob.glob(os.path.join(PROPOSE, "*", ".propose-run.jsonl")):
        wt = os.path.dirname(run)
        url = subprocess.run(["git", "-C", wt, "remote", "get-url", "origin"],
                             capture_output=True, text=True).stdout.strip()
        repo = url.rstrip("/").split("/")[-1].removesuffix(".git") or "?"
        lines = open(run, errors="replace").read().splitlines()
        tools, used = activity.tools_from_stream(lines)
        cost = 0.0
        for ln in lines:
            if '"type":"result"' in ln.replace(" ", ""):
                try:
                    cost = float(json.loads(ln).get("total_cost_usd") or 0)
                except ValueError:
                    pass
        change = re.sub(r"^session-(propose|archive)-|-(orchestrator|listener|unknown|edittest)-\d+$",
                        "", os.path.basename(wt))
        yield dict(kind="propose", agent="propose-session", project=repo,
                   model=activity.model_from_stream(lines), skills_used=used, tools=tools,
                   cost=cost, billing="api" if repo in API_REPOS else "subscription",
                   ref=f"backfill:propose:{change}", ts=os.path.getmtime(run))


def chat_rows():
    import bootstrap  # noqa: E402
    import keystore  # noqa: E402
    import relay  # noqa: E402
    stats = bootstrap.load_channels(ROOT).get("statistics")
    msgs = relay.get_messages(stats, keystore.lees("orchestrator"),
                              os.environ.get("BUZZ_RELAY_URL", "ws://192.168.178.60:3000")) or []
    for m in msgs:
        s = STAT.match((m.get("content") or "").strip())
        if not s:
            continue
        model = s.group(3).split("→")[-1].replace("⚠ DIFFERS", "").strip()
        yield dict(kind="chat", agent=s.group(1), project=s.group(2), model=model,
                   cost=float(s.group(5)), turns=int(s.group(4)),
                   billing="api" if s.group(2) == "convergence" else "subscription",
                   ref="backfill:statistics", ts=m.get("created_at", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", type=float, default=time.time())
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    counts = {}
    for source in (habitat_rows, propose_rows, chat_rows):
        for row in source():
            if row["ts"] >= a.before:
                continue
            counts[row["kind"]] = counts.get(row["kind"], 0) + 1
            if not a.dry_run:
                activity.record(**row)
    print("backfilled:", counts)


if __name__ == "__main__":
    main()
