# SPDX-License-Identifier: EUPL-1.2
"""Werksessies: een langere, LEZENDE claude-run die vanuit een kanaal start.

Een chat-beurt is één `claude -p` van 150s met Read/Grep/Glob. Dat is te klein
voor werk ("lees deze twaalf clips en zeg wat eruit moet"). Een werksessie is
hetzelfde subprocess, maar met minuten, een eigen werkmap en een eigen toolset —
en alles daarvan staat in `sessies.yml`, niet in de prompt.

Niet-blokkerend: de sessie draait losgekoppeld met stdout naar een runbestand;
`oogst()` leest per listener-tick het nieuwe stuk. Zo bevriest een sessie van een
kwartier de chat niet.
"""
import json
import os
import re
import signal
import subprocess
import time

import bootstrap
import providers

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RUNS = os.environ.get("SESSIE_RUNS", "/tmp/boomhuis-sessies")
MARKER = re.compile(r"^[ \t]*!sessie[ \t]+([a-z0-9_-]+)[ \t]*(.*)$", re.M | re.I)
# Nooit aan een sessie, ook niet als een type ze per ongeluk in `tools` zet.
VERBODEN = ["Write", "Edit", "NotebookEdit", "Bash", "Task", "KillShell"]
PROGRESS_MAX, PROGRESS_GAP = 6, 25


def laad(here):
    """sessies.yml lezen. Ontbreekt het bestand → geen types (fail-closed)."""
    try:
        return bootstrap.load_yaml(os.path.join(here, "sessies.yml")) or {}
    except OSError:
        return {"types": {}}


def lees_marker(tekst):
    """(type, opdracht) van de EERSTE `!sessie`-regel, of None. Alleen de eerste:
    één bericht zet hoogstens één sessie in gang."""
    m = MARKER.search(tekst or "")
    return (m.group(1).lower(), m.group(2).strip()) if m else None


def knip_marker(tekst):
    """De marker uit een te posten antwoord halen. Een geposte `!sessie`-regel zou
    later opnieuw gelezen kunnen worden; knippen maakt er een instructie van die
    precies één keer telt."""
    return MARKER.sub("", tekst or "", count=1).strip()


def mag_starten(cfg, typ, wie, lopend):
    """(ok, reden). Weigeren zonder reden bestaat niet: een stille weigering is
    niet te onderscheiden van een sessie die niets vond."""
    types = (cfg or {}).get("types") or {}
    if typ not in types:
        namen = ", ".join(sorted(types)) or "(geen)"
        return False, f"onbekend sessietype '{typ}' — beschikbaar: {namen}"
    if wie not in (types[typ].get("starters") or []):
        return False, f"@{wie} mag het type '{typ}' niet starten"
    if any(s["wie"] == wie for s in lopend):
        return False, f"@{wie} heeft al een sessie lopen — die eerst afwachten"
    if len(lopend) >= int(cfg.get("max_gelijktijdig") or 2):
        return False, "er lopen al maximaal sessies — later opnieuw"
    return True, ""


class Register:
    """De lopende sessies. Het runbestand ís de status; er is geen aparte wachtrij."""

    def __init__(self, cfg, runs=RUNS):
        self.cfg = cfg
        self.runs = runs
        self.lopend = []
        os.makedirs(runs, exist_ok=True)

    def start(self, typ, opdracht, wie, cname, cid):
        """Start losgekoppeld. Return (sessie, "") of (None, reden)."""
        ok, reden = mag_starten(self.cfg, typ, wie, self.lopend)
        if not ok:
            return None, reden
        t = self.cfg["types"][typ]
        werkmap = t.get("werkmap") or ""
        if not os.path.isdir(werkmap):
            return None, f"werkmap van '{typ}' bestaat niet: {werkmap}"
        tools = [x for x in (t.get("tools") or []) if x not in VERBODEN]
        cmd = [CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
               "--permission-mode", "dontAsk",
               "--append-system-prompt", t.get("systeem") or "",
               "--allowedTools", ",".join(providers.scoped(tools)),
               "--disallowedTools", ",".join(VERBODEN)]
        if t.get("model"):
            cmd += ["--model", t["model"]]
        pad = os.path.join(self.runs, f"{typ}-{wie}-{int(time.time())}.jsonl")
        prompt = (t.get("prompt") or "{opdracht}").replace("{opdracht}", opdracht)
        try:
            uit = open(pad, "w")
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=uit,
                                    stderr=subprocess.DEVNULL, text=True,
                                    cwd=werkmap, env=providers.agent_env(),
                                    start_new_session=True)
        except OSError as e:
            return None, f"kan de sessie niet starten: {str(e)[:100]}"
        try:
            proc.stdin.write(prompt)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        s = {"typ": typ, "wie": wie, "cid": cid, "cname": cname, "proc": proc,
             "pad": pad, "uit": uit, "offset": 0, "t0": time.time(),
             "identiteit": t.get("identiteit") or wie, "n": 0, "tp": 0.0,
             "max_s": int(t.get("max_seconden") or 900), "res": None}
        self.lopend.append(s)
        return s, ""

    def _nieuwe_events(self, s):
        """Wat er sinds de vorige tick in het runbestand bij kwam."""
        evs = []
        try:
            with open(s["pad"]) as f:
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
        klaar = 0
        for s in list(self.lopend):
            for ev in self._nieuwe_events(s):
                if ev.get("type") == "result":
                    s["res"] = ev
                elif ev.get("type") == "assistant":
                    self._voortgang(s, ev, post)
            op = time.time() - s["t0"]
            if s["proc"].poll() is None and op > s["max_s"]:
                self._stop(s)
                post(s, f"⏹️ sessie `{s['typ']}` afgekapt na {int(op // 60)} min "
                        f"(budget {s['max_s']}s). Wat tot dan gedaan is, staat hierboven.")
                self._sluit(s)
                klaar += 1
                continue
            if s["proc"].poll() is not None:
                post(s, self._resultaat(s, op))
                self._sluit(s)
                klaar += 1
        return klaar

    def _voortgang(self, s, ev, post):
        for c in (ev.get("message") or {}).get("content", []):
            if c.get("type") != "tool_use":
                continue
            nu = time.time()
            if s["n"] >= PROGRESS_MAX or (s["n"] and nu - s["tp"] < PROGRESS_GAP):
                continue
            s["n"], s["tp"] = s["n"] + 1, nu
            doel = providers._target(c.get("input") or {})
            post(s, f"⋯ sessie {s['typ']}: {c.get('name')} {doel}".strip())

    def _resultaat(self, s, op):
        """Altijd iets posten. Een sessie die stil niets oplevert leest als 'niets
        te melden', en dat is precies de false-clear die we niet willen."""
        r = s["res"] or {}
        antwoord = (r.get("result") or "").strip()
        voet = (f"— sessie `{s['typ']}` · {int(op // 60)}m{int(op % 60):02d}s"
                f" · ${float(r.get('total_cost_usd') or 0.0):.2f}"
                f" · {int(r.get('num_turns') or 0)} beurten")
        if not antwoord:
            return (f"⚠️ sessie `{s['typ']}` eindigde zonder antwoord "
                    f"(exit {s['proc'].returncode}). Log: {s['pad']}\n{voet}")
        if r.get("is_error"):
            antwoord = f"⚠️ sessie liep vast ({r.get('subtype') or 'error'}):\n{antwoord}"
        return f"{antwoord}\n\n{voet}"

    def _stop(self, s):
        try:
            os.killpg(os.getpgid(s["proc"].pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def _sluit(self, s):
        try:
            s["uit"].close()
        except OSError:
            pass
        if s in self.lopend:
            self.lopend.remove(s)
