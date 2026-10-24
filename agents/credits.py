# SPDX-License-Identifier: MIT
"""Work billed to Mark's API credits instead of his subscription.

Mark, 2026-10-24: Anthropic gives him $100 of API credits a month, unused,
and the game (MWest2020/convergence) is to run on them. Its assignment: "Stop
at a cost overrun and report it, instead of going on."

- **What is billed here**: chat turns in a channel with `billing: api` in
  channels.yml, and propose sessions and habitat builds for a repository in
  factory.yml `api_repos`. Everything else stays on the subscription.
- **The key** comes from `secrets/anthropic-api.yaml` (SOPS) at listener
  start and lives in this process only. It is added to a child's environment
  for billed work and never otherwise: `providers.agent_env()` passes no keys.
- **The ledger** (`~/.local/state/ratatoskr/api-ledger.jsonl`) records every
  billed cost; a month's total against `api_budget_usd` decides whether new
  billed work may start. A build first needs room for its whole budget.
"""
import json
import os
import subprocess
import time

import yaml

LEDGER = os.path.expanduser("~/.local/state/ratatoskr/api-ledger.jsonl")
_state = {"key": "", "budget": 0.0, "channels": set(), "repos": set()}


def load(root, factory, run=subprocess.run, log=print):
    """Read the key and the scope. Returns "" or why billed work is off."""
    _state["budget"] = float(factory.get("api_budget_usd") or 0)
    _state["repos"] = set(factory.get("api_repos") or [])
    try:
        chans = (yaml.safe_load(open(os.path.join(root, "channels.yml"))) or {})["channels"]
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        chans = {}
    _state["channels"] = {n for n, c in chans.items()
                          if isinstance(c, dict) and c.get("billing") == "api"}
    try:
        p = run(["sops", "-d", "--extract", '["anthropic_api_key"]',
                 os.path.join(root, "secrets", "anthropic-api.yaml")],
                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        p = None
        why = str(e)[:120]
    if p is not None and p.returncode == 0 and p.stdout.strip().startswith("sk-ant-"):
        _state["key"] = p.stdout.strip()
        return ""
    why = why if p is None else (p.stderr.strip() or "no key in the secret")[:120]
    log(f"[listener] API credits off: {why}", flush=True)
    return why


def channel_billed(cname):
    return cname in _state["channels"]


def repo_billed(repo):
    return str(repo).split("/")[-1] in _state["repos"]


def spent(now=time.time, ledger=LEDGER):
    """This month's billed total."""
    month = time.strftime("%Y-%m", time.localtime(now()))
    total = 0.0
    try:
        for ln in open(ledger):
            try:
                row = json.loads(ln)
            except ValueError:
                continue
            if time.strftime("%Y-%m", time.localtime(row.get("ts", 0))) == month:
                total += float(row.get("cost") or 0)
    except OSError:
        pass
    return total


def refusal(need=0.0, now=time.time, ledger=LEDGER):
    """"" when billed work costing up to `need` may start, else the reason."""
    if not _state["key"]:
        return "the API key is not loaded, so billed work is off"
    left = _state["budget"] - spent(now, ledger)
    if left <= need:
        return (f"this month's API budget is used up (${spent(now, ledger):.2f} of "
                f"${_state['budget']:.2f}" + (f"; this needs room for ${need:.2f}" if need else "")
                + ")")
    return ""


def env(base):
    """`base` with the API key, for billed work only."""
    return {**base, "ANTHROPIC_API_KEY": _state["key"]}


def record(kind, cost, ref, now=time.time, ledger=LEDGER):
    try:
        cost = float(cost or 0)
    except (TypeError, ValueError):
        return
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    with open(ledger, "a") as fh:
        fh.write(json.dumps({"ts": int(now()), "kind": kind, "cost": round(cost, 4),
                             "ref": ref}) + "\n")
