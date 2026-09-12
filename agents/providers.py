# SPDX-License-Identifier: EUPL-1.2
"""Provider-naad: het agent-backend zit achter één functie. Apart van listener.py
zodat die onder de ≤200-regel-conventie blijft. Vandaag 'claude-p' (sub-first);
een nieuw backend = één extra tak. De handbook-def declareert provider, model en
tools (front-matter agent.chat), en die worden hier afgedwongen — niet alleen
gedeclareerd (besluit Mark 2026-09-06: "afdwingen, niet yolo free for all").
"""
import json
import os
import subprocess
import time

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
MAX_TURN_S = 150

# Wat de agent-subprocess van de omgeving mág zien. De listener draagt de nsec van
# ELKE agent in zijn eigen omgeving; zonder deze filter erft elke beurt die sleutels
# (en de age-key, GitHub-token, ssh-agent) en is één geslaagde prompt-injectie
# genoeg om ze via /proc/self/environ te lezen en in het kanaal te posten.
ENV_KEEP = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TERM",
            "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME")

# Pad-tools worden begrensd tot de werkboom. `--allowedTools Read` alleen begrenst
# NIETS: geverifieerd 2026-09-06 dat een agent daarmee een bestand buiten de repo
# las zonder denial; met `Read(./**)` wordt diezelfde poging geweigerd én gemeld.
PATH_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "NotebookEdit"}


# Alleen deze drie mogen een tweede pad krijgen: lezen buiten de werkboom is
# soms nodig (een skill-forge-oordeel over een clip die in de zettelkast ligt),
# schrijven buiten de werkboom nooit.
READ_TOOLS = ("Read", "Grep", "Glob")


def scoped(tools, extra=None):
    """Pad-tools krijgen een werkboom-scope; de rest blijft zoals hij is.

    `extra` = expliciet gedeclareerde EXTRA leespaden (per sessietype in
    sessions.yml). Elk pad wordt een eigen, even strakke scope — niet een
    verruiming van de werkboom-scope, maar een tweede vergunning ernaast."""
    out = [f"{t}(./**)" if t in PATH_TOOLS else t for t in (tools or [])]
    for path in (extra or []):
        out += [f"{t}({path.rstrip('/')}/**)" for t in READ_TOOLS if t in (tools or [])]
    return out


def _target(inp):
    """Het interessante deel van een tool-aanroep, kort: een pad of een commando."""
    for k in ("file_path", "path", "pattern", "command", "url"):
        v = inp.get(k)
        if v:
            v = str(v)
            return (v[-48:] if len(v) > 48 else v)
    return ""


def agent_env():
    """Alleen wat de CLI nodig heeft — geen sleutels, geen tokens."""
    return {k: v for k, v in os.environ.items() if k in ENV_KEEP}


def main_model(usage, requested=None):
    """Het model dat het WERK deed, uit `modelUsage`.

    Eerder werd hier de eerste sleutel van die map genomen. Een run kan meerdere
    modellen aanraken, en dan noemde de statistiekregel er willekeurig één — precies
    het getal waarop je zou aflezen of het gedeclareerde model afgedwongen wordt.
    Nu: het model met de meeste tokens. Geen usage → wat er requested was."""
    if not isinstance(usage, dict) or not usage:
        return requested or ""

    def tokens(v):
        if not isinstance(v, dict):
            return 0
        return sum(x for k, x in v.items()
                   if isinstance(x, (int, float)) and "oken" in k)

    return max(usage, key=lambda k: tokens(usage[k]))


def model_matches(requested, actual):
    """Is het gedraaide model de familie die requested werd? De def noemt de
    intentie (haiku/sonnet/opus), de run een exacte id (claude-sonnet-5)."""
    if not requested:
        return True
    return requested.lower() in (actual or "").lower()


def run(provider, system, prompt, model=None, allow=None, deny=None, progress=None):
    """Draai één beurt. Return {answer, model, cost, turns, denials, error}.

    `denials` = de tool-aanroepen die de permissielaag heeft geweigerd; de
    listener meldt die per run in #escalatie zodat een mens beslist of de rol
    verruimd moet worden. Zonder dit veld zou een agent stil minder kunnen dan
    zijn mandaat belooft.
    """
    if provider not in (None, "claude-p", "claude"):
        return {"answer": f"(provider '{provider}' nog niet ondersteund door deze listener)",
                "model": "", "cost": 0.0, "turns": 0, "denials": [], "error": "provider"}

    # dontAsk = deny-by-default: alles buiten --allowedTools wordt geweigerd i.p.v.
    # aangeboden. Zonder deze vlag hield de agent tools als Agent, WebFetch en
    # SendMessage — de allowlist bepaalde alleen wat zónder vragen mocht. Gemeten
    # 2026-09-06: mét de vlag komt een WebFetch-poging als permission_denial terug,
    # zodat #escalatie een machinaal signaal krijgt en niet alleen zelfrapportage.
    cmd = [CLAUDE, "-p", "--output-format", "json", "--permission-mode", "dontAsk",
           "--append-system-prompt", system]
    if model:
        cmd += ["--model", model]
    if allow:
        cmd += ["--allowedTools", ",".join(scoped(allow))]
    if deny:
        cmd += ["--disallowedTools", ",".join(deny)]
    # Prompt via stdin, niet als argument: --allowedTools/--disallowedTools zijn
    # variadisch (`<tools...>`) en slikken een daaropvolgend positioneel argument op
    # ("Input must be provided either through stdin or as a prompt argument").
    # Streamen i.p.v. wachten: met stream-json komt elke stap binnen zodra hij
    # gebeurt, zodat de listener kan laten zien WAT de agent doet in plaats van
    # anderhalve minuut stilte. `progress` krijgt korte regels ("Read providers.py").
    cmd += ["--output-format", "stream-json", "--verbose"]
    t0 = time.time()
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=agent_env())
    except OSError as e:
        return {"answer": f"(kan {CLAUDE} niet starten)", "model": model or "", "cost": 0.0,
                "turns": 0, "denials": [], "error": str(e)[:120]}
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except BrokenPipeError:
        pass

    d = {}
    for line in proc.stdout:
        if time.time() - t0 > MAX_TURN_S:
            proc.kill()
            return {"answer": "(time-out)", "model": model or "", "cost": 0.0,
                    "turns": 0, "denials": [], "error": "timeout"}
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            d = ev
        elif ev.get("type") == "assistant" and progress:
            for c in (ev.get("message") or {}).get("content", []):
                if c.get("type") == "tool_use":
                    progress(f"{c.get('name')} {_target(c.get('input') or {})}".strip())
    proc.wait(timeout=10)
    if not d:
        err = (proc.stderr.read() or "").strip()[:200]
        return {"answer": "(geen antwoord)", "model": model or "", "model_requested": model or "", "cost": 0.0,
                "turns": 0, "denials": [], "error": err or "geen resultaat-event"}

    return {"answer": (d.get("result") or "").strip() or "(geen antwoord)",
            "model": main_model(d.get("modelUsage"), model),
            "model_requested": model or "",
            "cost": float(d.get("total_cost_usd") or 0.0),
            "turns": int(d.get("num_turns") or 0),
            "denials": d.get("permission_denials") or [],
            "error": "" if not d.get("is_error") else str(d.get("subtype") or "error")}
