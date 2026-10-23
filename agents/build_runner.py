# SPDX-License-Identifier: MIT
"""Running habitat's chain in the background and following it.

The chain takes up to two hours (four Jobs of up to 30 minutes each), and the
listener's poll loop must never wait for it. So `start` launches
`dispatch/chain.sh` detached, with its output in a run file, and `tick` reads
what is new on every loop round. That is the pattern of sessions.Register.

What `tick` reads is what chain.sh and dispatch.sh print, and nothing else:

    === keten: rol builder ===
    [dispatch] branch=habitat/builder/<change>-<run>
    [dispatch] 4 artefact(en) -> <logdir>/artifacts/<repo>/<run>
    keten: builder -> habitat/builder/<change>-<run>          (role passed)
    keten: rol builder niet geslaagd (dispatch exit 1) ...    (role failed)
    keten klaar — builder-branch: <branch>                    (chain passed)
"""
import json
import os
import re
import subprocess
import time

import detach

ROLE = re.compile(r"^=== keten: rol (\w+) ===")
BRANCH = re.compile(r"^\[dispatch\] branch=(\S+)")
STORE = re.compile(r"^\[dispatch\] \d+ artefact\(en\) -> (\S+)")
PASSED = re.compile(r"^keten: (\w+) -> (\S+)")
FAILED = re.compile(r"^keten: rol (\w+) niet geslaagd(.*)$")
DONE = re.compile(r"^keten klaar — builder-branch: (\S+)")


def events(lines):
    """[(kind, role, detail)] for the lines of a chain run, in order."""
    out, store = [], ""
    for ln in lines:
        if m := ROLE.match(ln):
            store = ""
        elif m := STORE.match(ln):
            store = m.group(1)
        elif m := PASSED.match(ln):
            out.append(("passed", m.group(1), {"branch": m.group(2), "store": store}))
        elif m := FAILED.match(ln):
            out.append(("failed", m.group(1), {"why": m.group(2).strip(" —"), "store": store}))
        elif m := DONE.match(ln):
            out.append(("done", "chain", {"branch": m.group(1)}))
    return out


def report(store):
    """The run report's verdict, cost and turns, or {} when there is none."""
    try:
        return json.load(open(os.path.join(store, "run-report.json")))
    except (OSError, ValueError, TypeError):
        return {}


def comment(kind, role, detail):
    """The issue comment for one event: the trail Mark asked for."""
    if kind == "done":
        return f"**Chain passed.** Builder branch: `{detail['branch']}`."
    r = report(detail.get("store"))
    shown = {"verdict": r.get("verdict"), "turns": r.get("num_turns"),
             "cost": f"${r['total_cost_usd']:.2f}" if isinstance(r.get("total_cost_usd"),
                                                                (int, float)) else None}
    facts = ", ".join(f"{k} {v}" for k, v in shown.items() if v is not None)
    if kind == "passed":
        return f"**{role}: PASS** ({facts or 'no run report'}). Branch `{detail['branch']}`."
    why = r.get("subtype") if r.get("subtype") not in (None, "success") else ""
    return (f"**{role}: FAIL** ({facts or 'no run report'})"
            + (f", stopped by `{why}`" if why else "") + f". {detail.get('why') or ''}").strip()


class Pid:
    """A chain started by an EARLIER listener: not our child, so poll by pid."""

    def __init__(self, pid):
        self.pid = pid

    def poll(self):
        try:
            os.kill(self.pid, 0)
        except (ProcessLookupError, PermissionError, TypeError):
            return -1     # gone; its exit code went to the listener that started it
        return None


class Builds:
    """Running chains and PRs waiting for CI, kept in a state file so a listener
    restart (every deploy) picks them up again instead of losing their trail."""

    def __init__(self, cfg, popen=subprocess.Popen, now=time.time):
        self.cfg, self.popen, self.now = cfg, popen, now
        os.makedirs(cfg["runs"], exist_ok=True)
        self.state = os.path.join(cfg["runs"], "state.json")
        try:
            with open(self.state) as fh:
                st = json.load(fh)
        except (OSError, ValueError):
            st = {}
        self.running = [{**b, "proc": Pid(b.get("pid"))} for b in st.get("running", [])]
        self.merging = st.get("merging", [])
        self.deploying = st.get("deploying", [])
        # propose sessions too: a restart (every deploy) must not orphan one
        self.proposing = [{**j, "proc": Pid(j.get("pid"))} for j in st.get("proposing", [])]

    def save(self):
        keep = [{k: v for k, v in b.items() if k != "proc"} for b in self.running]
        tmp = self.state + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({"running": keep, "merging": self.merging, "deploying": self.deploying,
                       "proposing": [{k: v for k, v in j.items() if k != "proc"}
                                     for j in self.proposing]}, fh)
        os.replace(tmp, self.state)

    def start(self, repo, change, issue, cname, cid, starter):
        path = os.path.join(self.cfg["runs"], f"{repo}-{change}-{int(self.now())}.log")
        out = open(path, "w")
        out.write(json.dumps({"repo": repo, "change": change, "issue": issue, "channel": cname,
                              "starter": starter, "started": int(self.now())}) + "\n")
        out.flush()
        env = dict(os.environ, WORKER_IMAGE=self.cfg["worker_image"],
                   KUBECTL=self.cfg["kubectl"], HABITAT_LOGDIR=self.cfg["logdir"],
                   CLAUDE_CREDS_FILE="",
                   HABITAT_MAX_BUDGET_USD=f"{float(self.cfg.get('max_budget_usd', 5)):.2f}")
        proc = self.popen(detach.argv([os.path.join(self.cfg["habitat_dir"], "dispatch",
                                                    "chain.sh"),
                                       change, f"{self.cfg['owner']}/{repo}"]),
                          stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                          env=env, cwd=self.cfg["habitat_dir"], start_new_session=True)
        out.close()  # the child holds its own descriptor
        b = {"repo": repo, "change": change, "issue": issue, "cid": cid, "cname": cname, "path": path,
             "proc": proc, "pid": getattr(proc, "pid", None), "seen": 0}
        self.running.append(b)
        self.save()
        return b

    def tick(self, on_event):
        """Report what is new; drop chains that have ended."""
        changed = False
        for b in list(self.running):
            code = b["proc"].poll()          # before reading: an exit's last lines count
            with open(b["path"]) as fh:
                lines = fh.read().splitlines()[1:]
            evs = events(lines)
            if code is not None:
                # off the list before any event: a failure wakes the hub, whose
                # retry was refused as "another build is still running" (2026-10-23)
                self.running.remove(b)
                self.save()
                changed = True
            for kind, role, detail in evs[b["seen"]:]:
                on_event(b, kind, role, detail)
                changed = True
            b["seen"] = len(evs)
            if code is not None and not any(k in ("failed", "done") for k, _, _ in evs):
                tail = " / ".join(lines[-3:])[-300:] or "no output"
                on_event(b, "failed", "chain", {"why": f"exit {code}: {tail}"})
        if changed:
            self.save()
