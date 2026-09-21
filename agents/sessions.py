# SPDX-License-Identifier: MIT
"""Work sessions: a longer claude run started from a channel.

A chat turn is one `claude -p` of 150s with Read/Grep/Glob. That is too small
for work ("read these twelve clips and say what has to go"). A work session is
the same subprocess, but with minutes, its own working directory and its own
toolset — and all of that lives in `sessions.yml`, not in the prompt.

Non-blocking: the session runs detached with stdout going to a run file;
`tick()` reads the new part on every listener tick. That way a quarter-hour
session does not freeze the chat.
"""
import json
import os
import signal
import subprocess
import time

import bootstrap
import providers
import session_gate
import session_report
import work_tree

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RUNS = os.environ.get("SESSIE_RUNS", "/tmp/boomhuis-sessies")
# Reading/stripping the marker and the authorisation live in session_gate.py
# (pure); what stays here is only what touches processes and files.
read_marker = session_gate.read_marker
read_own_marker = session_gate.read_own_marker
strip_marker = session_gate.strip_marker
strip_own_marker = session_gate.strip_own_marker

# Never given to a READING session, not even when a type puts them in `tools` by
# mistake. A writing session (`writes: true`) does need them — it works in a
# worktree of its own with a pre-push hook as the fence, see work_tree.py.
FORBIDDEN = ["Write", "Edit", "NotebookEdit", "Bash", "Task", "KillShell"]
# A writing session does not get these either: Task spawns agents out of all
# sight, KillShell touches processes that are not its own.
ALWAYS_FORBIDDEN = ["Task", "KillShell"]
# Where the worktrees of writing sessions go — outside every running checkout.
WORKTREE_BASE = os.environ.get("SESSIE_WERKMAPPEN", "/home/agent/sessie-werk")
PROGRESS_MAX, PROGRESS_GAP = 6, 25


def load(here):
    """Read sessions.yml. No file → no types (fail-closed)."""
    try:
        return bootstrap.load_yaml(os.path.join(here, "sessions.yml")) or {}
    except OSError:
        return {"types": {}}


class Register:
    """The running sessions. The run file IS the status; there is no queue."""

    def __init__(self, cfg, runs=RUNS):
        self.cfg = cfg
        self.runs = runs
        self.running = []
        os.makedirs(runs, exist_ok=True)

    def start(self, type_name, task, starter, requester, cname, cid, message_id=""):
        """Start detached. Returns (session, "") or (None, reason).

        `starter` wrote the marker, `requester` is the person it is done for —
        for a human typing it themselves the two are the same."""
        ok, reason = session_gate.may_start(self.cfg, type_name, starter, requester,
                                            self.running)
        if not ok:
            return None, reason
        t = self.cfg["types"][type_name]
        writes = bool(t.get("writes"))
        workdir = t.get("workdir") or ""
        branch = ""
        if writes:
            # A fresh worktree on its own branch, WITH a pre-push hook. If that
            # fails nothing starts: better no session than one that writes in a
            # running checkout.
            try:
                workdir, branch = work_tree.create(workdir, WORKTREE_BASE,
                                                  type_name, requester)
            except Exception as e:
                return None, f"kon geen werkboom maken voor '{type_name}': {str(e)[:140]}"
        elif not os.path.isdir(workdir):
            return None, f"werkmap van '{type_name}' bestaat niet: {workdir}"
        forbidden = ALWAYS_FORBIDDEN if writes else FORBIDDEN
        tools = [x for x in (t.get("tools") or []) if x not in forbidden]
        cmd = [CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
               "--permission-mode", "dontAsk",
               "--append-system-prompt", t.get("system") or "",
               "--allowedTools", ",".join(providers.scoped(tools, t.get("also_reads"))),
               "--disallowedTools", ",".join(forbidden)]
        if t.get("model"):
            cmd += ["--model", t["model"]]
        # File name after the REQUESTER: otherwise every session odin starts is
        # called odin, and afterwards you cannot see who it ran for.
        path = os.path.join(self.runs, f"{type_name}-{requester}-{int(time.time())}.jsonl")
        prompt = (t.get("prompt") or "{task}").replace("{task}", task)
        try:
            out = open(path, "w")
            # First line: who, on whose behalf, where. Before the process starts,
            # so the provenance is there even if the session dies immediately.
            # The tick skips unknown types, so this disturbs nothing.
            json.dump({"type": "boomhuis_session", "session_type": type_name,
                       "starter": starter, "requester": requester, "channel": cname,
                       "message": message_id, "writes": writes, "branch": branch,
                       "workdir": workdir, "started": int(time.time())}, out)
            out.write("\n")
            out.flush()
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=out,
                                    stderr=subprocess.DEVNULL, text=True,
                                    cwd=workdir, env=providers.agent_env(),
                                    start_new_session=True)
        except OSError as e:
            return None, f"kan de sessie niet starten: {str(e)[:100]}"
        try:
            proc.stdin.write(prompt)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        s = {"type": type_name, "starter": starter, "requester": requester,
             "cid": cid, "cname": cname, "proc": proc,
             "path": path, "out": out, "offset": 0, "t0": time.time(),
             "identity": t.get("identity") or starter, "n": 0, "tp": 0.0,
             "max_s": int(t.get("max_seconds") or 900), "res": None,
             "writes": writes, "branch": branch, "workdir": workdir}
        self.running.append(s)
        return s, ""

    def _new_events(self, s):
        """What was added to the run file since the previous tick."""
        evs = []
        try:
            with open(s["path"]) as f:
                f.seek(s["offset"])
                for line in f:
                    if not line.endswith("\n"):   # half a line: retry next tick
                        break
                    s["offset"] += len(line)
                    try:
                        evs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return evs

    def tick(self, post):
        """Progress and completion. `post(session, text)` does the posting; this
        module knows no keys. Returns the number of finished sessions."""
        done = 0
        for s in list(self.running):
            for ev in self._new_events(s):
                if ev.get("type") == "result":
                    s["res"] = ev
                elif ev.get("type") == "assistant":
                    self._progress(s, ev, post)
            elapsed = time.time() - s["t0"]
            if s["proc"].poll() is None and elapsed > s["max_s"]:
                self._stop(s)
                post(s, f"⏹️ sessie `{s['type']}` afgekapt na {int(elapsed // 60)} min "
                        f"(budget {s['max_s']}s). Wat tot dan gedaan is, staat hierboven.")
                self._close(s)
                done += 1
                continue
            if s["proc"].poll() is not None:
                post(s, session_report.result_text(s, elapsed))
                self._close(s)
                done += 1
        return done

    def _progress(self, s, ev, post):
        for c in (ev.get("message") or {}).get("content", []):
            if c.get("type") != "tool_use":
                continue
            now = time.time()
            if s["n"] >= PROGRESS_MAX or (s["n"] and now - s["tp"] < PROGRESS_GAP):
                continue
            s["n"], s["tp"] = s["n"] + 1, now
            target = providers._target(c.get("input") or {})
            post(s, f"⋯ sessie {s['type']}: {c.get('name')} {target}".strip())

    def _stop(self, s):
        try:
            os.killpg(os.getpgid(s["proc"].pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def _close(self, s):
        try:
            s["out"].close()
        except OSError:
            pass
        if s in self.running:
            self.running.remove(s)
