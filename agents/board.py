# SPDX-License-Identifier: MIT
"""Each project's GitHub board follows the factory (Mark, 2026-10-24: "perhaps
we need to update a board on my github ... to monitor status on it").

factory.yml `boards: {repo: project number}` names the boards. Every issue
comment and issue the listener writes already marks a stage, so `note()` is
called from `issues.create`/`issues.comment` and moves the issue's card:

    propose issue opened        -> Writing change
    "Build started ..."         -> Building
    "PR #n opened ..."          -> CI
    a FAIL, "Not merged", "No PR", "Not deployed", ...  -> Blocked
    "Merged PR #n ..."          -> Done when the merge closed the issue (a build),
                                   Todo when it stays open (a proposal, now to build)
    "Deployed to the homelab"   -> Deployed

The projects' built-in "Item closed" workflow is off and the API cannot turn
it on, so Done is set here too: the background mover asks gh whether the
issue is closed. The gh calls run in a
detached child, so a slow API never holds up the listener; off until
`enable()` (tests never call it).
"""
import json
import os
import subprocess
import sys
import time

STATE = os.path.expanduser("~/.local/state/ratatoskr/board-fields.json")
BLOCKED = ("No PR:", "Not started:", "Not merged:", "Not deployed:", "Deploy stopped",
           "Could not open the PR", "Not archived:", "Merge of PR")
_cfg = {}


def enable(cfg):
    _cfg.clear()
    _cfg.update({"owner": cfg.get("owner", "MWest2020"), "boards": cfg.get("boards") or {}})


def stage_for(text, title=None):
    """The board stage a listener text marks, or None for no move."""
    t = (text or "").strip()
    if title is not None:
        return "Writing change" if title.startswith("propose:") else "Todo"
    if t.startswith("Build started"):
        return "Building"
    if ": FAIL**" in t.split("\n", 1)[0] or t.startswith(BLOCKED):
        return "Blocked"
    if t.startswith("PR #") and " opened" in t.split("\n", 1)[0]:
        return "CI"
    if t.startswith("Deployed to the homelab"):
        return "Deployed"
    if t.startswith("Merged PR"):
        return "Merged"          # resolved to Done or Todo by the mover
    return None


def note(repo, number, text, title=None, popen=subprocess.Popen):
    """Move the card for this issue, in the background, when the repo has a board."""
    name = str(repo).split("/")[-1]
    project = (_cfg.get("boards") or {}).get(name)
    stage = stage_for(text, title)
    if not project or not stage or not number:
        return None
    return popen([sys.executable, os.path.abspath(__file__), "move", _cfg["owner"], name,
                  str(project), str(int(number)), stage],
                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL, start_new_session=True)


def _gh(args):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[-200:])
    return p.stdout


def _fields(owner, project):
    """(project id, Status field id, {option: id}), cached per project."""
    try:
        cache = json.load(open(STATE))
    except (OSError, ValueError):
        cache = {}
    key = f"{owner}/{project}"
    if key not in cache:
        pid = json.loads(_gh(["project", "view", project, "--owner", owner,
                              "--format", "json"]))["id"]
        f = next(x for x in json.loads(_gh(["project", "field-list", project, "--owner", owner,
                                            "--format", "json"]))["fields"]
                 if x["name"] == "Status")
        cache[key] = [pid, f["id"], {o["name"]: o["id"] for o in f["options"]}]
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(cache, open(STATE, "w"))
    return cache[key]


def move(owner, repo, project, number, stage):
    if stage == "Merged":
        time.sleep(15)           # the "Closes #n" of the merge lands a moment later
        state = _gh(["issue", "view", number, "--repo", f"{owner}/{repo}", "--json", "state",
                     "--jq", ".state"]).strip()
        stage = "Done" if state == "CLOSED" else "Todo"
    pid, fid, options = _fields(owner, project)
    item = json.loads(_gh(["project", "item-add", project, "--owner", owner, "--url",
                           f"https://github.com/{owner}/{repo}/issues/{number}",
                           "--format", "json"]))["id"]
    _gh(["project", "item-edit", "--id", item, "--project-id", pid, "--field-id", fid,
         "--single-select-option-id", options[stage]])


if __name__ == "__main__" and sys.argv[1:2] == ["move"]:
    move(*sys.argv[2:7])
