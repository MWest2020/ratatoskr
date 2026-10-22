# SPDX-License-Identifier: MIT
"""Who in a shared room takes a message nobody was named in.

One small model call without tools reads the message and each member's contract
("Takes", "Not mine") and names the owner. Rejected (design.md): letting every
agent decide for itself — one turn per member, and they race each other, which is
the overlap again — and odin as the triage, a hub that tends to answer itself.

The answer is validated against the room: an owner that is not a member, a repo
the room does not list, or anything that is not the JSON asked for is a failed
triage, and a failed triage is said in the room.
"""
import json
import re

import providers

MODEL = "haiku"
MAX_OWNERS = 2

SYSTEM = (
    "You assign a message in a shared work room to the agent whose contract "
    "covers it. Read each contract's 'Takes' and 'Not mine'. Pick ONE owner; two "
    "only when the message holds two separate requests. Pick the repository the "
    "work is about from the list. Answer with JSON only, no prose:\n"
    '{"owners": ["<agent>"], "repo": "<repo>", "title": "<the work in at most 10 '
    'words>", "reason": "<one line, quoting the contract field that decided it>"}\n'
    'If no contract covers it: {"owners": [], "reason": "<why>"}')


def contract_lines(contract):
    """The fields triage needs, so a long contract does not drown the message."""
    keep = ("takes", "not mine", "produces")
    out, on = [], False
    for ln in (contract or "").splitlines():
        head = ln.lower().lstrip("- *")
        if head.startswith(keep):
            on = True
        elif ln.startswith("- **"):
            on = False
        if on and ln.strip():
            out.append(ln.strip())
    return "\n".join(out)


def prompt(content, room, agents):
    parts = [f"Agent {h}:\n{contract_lines(agents[h].get('contract'))}"
             for h in room["members"] if h in agents]
    return ("Contracts:\n\n" + "\n\n".join(parts)
            + f"\n\nRepositories: {', '.join(room['repos'])}"
            + f"\n\nMessage:\n{content}")


def parse(answer, room):
    """{owners, repo, title, reason} or (None, why)."""
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        return None, "triage gave no JSON"
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, f"triage gave broken JSON ({e.msg})"
    owners = d.get("owners")
    if not isinstance(owners, list):
        return None, "triage gave no owner list"
    stray = [o for o in owners if o not in room["members"]]
    if stray:
        return None, f"triage named {stray}, not members of this room"
    if not owners:
        return None, f"nobody's contract covers this: {d.get('reason') or 'no reason given'}"
    repo = d.get("repo") if d.get("repo") in room["repos"] else room["repos"][0]
    title = " ".join(str(d.get("title") or "").split())[:80]
    return {"owners": owners[:MAX_OWNERS], "repo": repo, "title": title,
            "reason": str(d.get("reason") or "").strip()[:200]}, ""


def run(content, room, agents, runner=providers.run):
    r = runner("claude-p", SYSTEM, prompt(content, room, agents), model=MODEL,
               no_tools=True)
    if r.get("error"):
        return None, f"triage did not run: {r['error']}"
    return parse(r.get("answer"), room)
