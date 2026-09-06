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

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
MAX_TURN_S = 150


def run(provider, system, prompt, model=None, allow=None, deny=None):
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
        cmd += ["--allowedTools", ",".join(allow)]
    if deny:
        cmd += ["--disallowedTools", ",".join(deny)]
    # Prompt via stdin, niet als argument: --allowedTools/--disallowedTools zijn
    # variadisch (`<tools...>`) en slikken een daaropvolgend positioneel argument op
    # ("Input must be provided either through stdin or as a prompt argument").
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           timeout=MAX_TURN_S)
    except subprocess.TimeoutExpired:
        return {"answer": "(time-out)", "model": model or "", "cost": 0.0,
                "turns": 0, "denials": [], "error": "timeout"}
    try:
        d = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        # Geen JSON = de CLI is gestruikeld vóór het eindobject; stdout is dan het
        # enige spoor. Niet stil slikken: de listener meldt dit als storing.
        return {"answer": (p.stdout or "").strip() or "(geen antwoord)",
                "model": model or "", "cost": 0.0, "turns": 0, "denials": [],
                "error": (p.stderr or "").strip()[:200] or "geen json"}

    used = list(d.get("modelUsage") or {})
    return {"answer": (d.get("result") or "").strip() or "(geen antwoord)",
            "model": used[0] if used else (model or ""),
            "cost": float(d.get("total_cost_usd") or 0.0),
            "turns": int(d.get("num_turns") or 0),
            "denials": d.get("permission_denials") or [],
            "error": "" if not d.get("is_error") else str(d.get("subtype") or "error")}
