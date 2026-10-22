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
    # The message is DATA to route, fenced off and never addressed to the model:
    # on 2026-10-22 "what's the status on the pending work?" got an answer
    # ("I need more context ...") instead of a routing, 2 runs out of 3.
    return ("Route the message below to an agent. Do NOT answer it, do not ask "
            "about it, do not comment on it: you only decide who owns it.\n\n"
            "Contracts:\n\n" + "\n\n".join(parts)
            + f"\n\nRepositories: {', '.join(room['repos'])}"
            + f"\n\nMessage to route:\n<<<\n{content}\n>>>\n\n"
            "Reply with the JSON object only.")


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


def run(content, room, agents, runner=providers.run, attempts=2):
    """One retry when the answer is not the JSON asked for: a small model now and
    then answers in prose, and that is a failed call, not a verdict."""
    for _ in range(attempts):
        r = runner("claude-p", SYSTEM, prompt(content, room, agents), model=MODEL,
                   no_tools=True)
        if r.get("error"):
            return None, f"triage did not run: {r['error']}"
        d, err = parse(r.get("answer"), room)
        if d or "JSON" not in err:
            return d, err
    return None, err
