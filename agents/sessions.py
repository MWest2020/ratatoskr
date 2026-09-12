# SPDX-License-Identifier: EUPL-1.2
"""Werksessies: een langere claude-run die vanuit een kanaal start.

Een chat-beurt is één `claude -p` van 150s met Read/Grep/Glob. Dat is te klein
voor werk ("lees deze twaalf clips en zeg wat eruit moet"). Een werksessie is
hetzelfde subprocess, maar met minuten, een eigen werkmap en een eigen toolset —
en alles daarvan staat in `sessions.yml`, niet in de prompt.

Niet-blokkerend: de sessie draait losgekoppeld met stdout naar een runbestand;
`tick()` leest per listener-tick het nieuwe stuk. Zo bevriest een sessie van een
kwartier de chat niet.
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
# Marker lezen/knippen en de machtiging staan in session_gate.py (puur);
# hier blijft alleen wat processen en bestanden aanraakt.
read_marker = session_gate.read_marker
strip_marker = session_gate.strip_marker

# Nooit aan een LEZENDE sessie, ook niet als een type ze per ongeluk in `tools`
# zet. Een schrijvende sessie (`writes: true`) heeft ze wél nodig — die werkt in
# een eigen worktree met een pre-push-hook als hek, zie work_tree.py.
FORBIDDEN = ["Write", "Edit", "NotebookEdit", "Bash", "Task", "KillShell"]
# Ook een schrijvende sessie krijgt deze niet: Task spawnt agents buiten elk
# zicht, KillShell raakt processen die niet van hem zijn.
ALWAYS_FORBIDDEN = ["Task", "KillShell"]
# Waar de worktrees van schrijvende sessies komen — buiten elke draaiende checkout.
WORKTREE_BASE = os.environ.get("SESSIE_WERKMAPPEN", "/home/agent/sessie-werk")
PROGRESS_MAX, PROGRESS_GAP = 6, 25


def load(here):
    """sessions.yml lezen. Ontbreekt het bestand → geen types (fail-closed)."""
    try:
        return bootstrap.load_yaml(os.path.join(here, "sessions.yml")) or {}
    except OSError:
        return {"types": {}}


class Register:
    """De lopende sessies. Het runbestand ís de status; er is geen aparte wachtrij."""

    def __init__(self, cfg, runs=RUNS):
        self.cfg = cfg
        self.runs = runs
        self.running = []
        os.makedirs(runs, exist_ok=True)

    def start(self, type_name, task, starter, requester, cname, cid, message_id=""):
        """Start losgekoppeld. Return (sessie, "") of (None, reason).

        `starter` schreef de marker, `requester` is degene namens wie het gaat —
        bij een mens die zelf typt zijn ze gelijk."""
        ok, reason = session_gate.may_start(self.cfg, type_name, starter, requester,
                                            self.running)
        if not ok:
            return None, reason
        t = self.cfg["types"][type_name]
        writes = bool(t.get("writes"))
        workdir = t.get("workdir") or ""
        branch = ""
        if writes:
            # Verse worktree op een eigen branch, mét pre-push-hook. Faalt dat,
            # dan start er niets: liever geen sessie dan een sessie die in een
            # draaiende checkout schrijft.
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
        # Bestandsnaam op de REQUESTER: anders heet elke door odin gestarte sessie
        # odin, en is achteraf niet te zien voor wie hij liep.
        path = os.path.join(self.runs, f"{type_name}-{requester}-{int(time.time())}.jsonl")
        prompt = (t.get("prompt") or "{task}").replace("{task}", task)
        try:
            out = open(path, "w")
            # Eerste regel: wie, namens wie, waar. Vóór het proces start, zodat de
            # herkomst er ook staat als de sessie meteen sneuvelt. De tick slaat
            # onbekende types over, dus dit stoort niets.
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
        """Wat er sinds de vorige tick in het runbestand bij kwam."""
        evs = []
        try:
            with open(s["path"]) as f:
                f.seek(s["offset"])
                for line in f:
                    if not line.endswith("\n"):   # halve regel: volgende tick opnieuw
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
        """Voortgang en afronding. `post(sessie, tekst)` doet het posten; deze
        module kent geen sleutels. Return het aantal afgeronde sessies."""
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
