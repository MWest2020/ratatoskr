# SPDX-License-Identifier: EUPL-1.2
"""Provider-naad: het agent-backend zit achter één functie. Apart van listener.py
zodat die onder de ≤200-regel-conventie blijft. Vandaag 'claude-p' (sub-first);
een nieuw backend = één extra tak. De handbook-def declareert de provider
(front-matter agent.provider, default claude-p).
"""
import os
import subprocess

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
MAX_TURN_S = 150


def run(provider, system, prompt):
    if provider in (None, "claude-p", "claude"):
        p = subprocess.run([CLAUDE, "-p", "--append-system-prompt", system, prompt],
                           capture_output=True, text=True, timeout=MAX_TURN_S)
        return (p.stdout or "").strip() or "(geen antwoord)"
    # hier pluggen toekomstige backends in (codex, remote-agent, http/SSE-connector…)
    return f"(provider '{provider}' nog niet ondersteund door deze listener)"
