# SPDX-License-Identifier: MIT
"""A handbook agent definition as text -> what the listener runs on. Pure (no
I/O), split from bootstrap.py so both stay under the 200-line convention, and so
the tests can feed it the real handbook layout."""
import re

import yaml

CONTRACT_INTRO = ("\n\nYOUR CONTRACT, from your handbook definition. Answer only what "
                  "it says you take; for anything under 'Not mine', name whose it is "
                  "and stop:\n")


def section(body, heading):
    """The text under `## <heading>` up to the next `## `, or "".

    Hyphen or space between the words, any case. The English translation of the
    handbook (2026-09-22) turned `## Chat-facet` into `## Chat facet`, and the
    regex here only knew the hyphen: every chat agent ran with an EMPTY system
    prompt for a month. Measured 2026-10-22: 8 of 8 agents at 0 characters."""
    words = r"[-\s]+".join(re.escape(w) for w in heading.split())
    m = re.search(rf"^##\s*{words}\b[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.S | re.M | re.I)
    return m.group(1) if m else ""


def blockquote(text):
    """The lines of `text` that are a markdown blockquote, without the `>`."""
    return "\n".join(ln[2:] if ln.startswith("> ") else ln[1:]
                     for ln in text.splitlines() if ln.startswith(">")).strip()


def parse_def(s):
    """A handbook definition as text -> the dict the listener runs on, or None.
    Pure, so the tests can feed it the real heading formats."""
    m = re.match(r"^---\n(.*?)\n---", s, re.S)
    if not m:
        return None
    fm = yaml.safe_load(m.group(1)).get("agent", {})
    chat = fm.get("chat") or {}
    channels = chat.get("channels") or []  # `or` also catches `channels:` = YAML null
    # system prompt = the blockquote under '## Chat facet', plus the role's
    # contract (openspec change role-contracts): who takes what is only a
    # boundary if the model is told, not only the reader of the handbook.
    system = blockquote(section(s[m.end():], "Chat facet"))
    contract = section(s[m.end():], "Contract").strip()
    if system and contract:
        system += CONTRACT_INTRO + contract
    provider = (fm.get("provider") or "claude-p")
    # Model and tools come from the registry and are enforced (Mark's decision,
    # 2026-09-06). Fail-closed: without a model the agent does not run — otherwise
    # it silently falls back on the environment default and nobody knows what it
    # ran on.
    tools = chat.get("tools") or {}
    # `routes` = de kanalen waar deze agent de woorden van de mens naartoe mag
    # doorsturen (routing.py). Uit de handbook, net als de rest van het mandaat:
    # zo staat het recht op één plek en niet in een prompt of een lokale yaml.
    return {"npub": fm.get("npub"), "channels": channels, "system": system,
            "contract": contract,
            "provider": provider, "model": chat.get("model") or "",
            "allow": tools.get("allow") or [], "deny": tools.get("deny") or [],
            "routes": chat.get("routes") or [],
            "skills": chat.get("skills") or []}
