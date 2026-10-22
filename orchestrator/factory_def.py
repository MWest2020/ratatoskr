# SPDX-License-Identifier: MIT
"""The factory's pure part: a role spec in, a handbook definition out.

Mark, 2026-10-22: "odin can decide for new roles if need be ... factory pattern
should be agent -> skills -> tool usage. clearly defined." A role is not
hand-written: odin gives a spec, and everything the handbook gate checks is
derived from it here, so a role is right by construction:

    tools.allow = Read, Grep, Glob + the `tools` of its skills (skill register)
    tools.deny  = Write, Edit, and Bash unless a skill brings a Bash rule

    name: scout                      # new; an existing role is Mark's to change
    model: sonnet                    # haiku | sonnet | opus
    channels: [werkplaats]           # existing channels only
    skills: [read-state]             # promoted skills from the register
    mandate: One paragraph.
    contract: {takes, produces, done_when, hands_off_to, not_mine}
    prompt: You are 'scout', ...
"""
import re

BASE = ["Read", "Grep", "Glob"]
MODELS = {"haiku", "sonnet", "opus"}
NAME = re.compile(r"^[a-z][a-z0-9-]{2,20}$")
FIELDS = (("takes", "Takes"), ("produces", "Produces"), ("done_when", "Done when"),
          ("hands_off_to", "Hands off to"), ("not_mine", "Not mine"))
RESERVED = {"mark", "orchestrator", "odin", "index"}


def tools_for(skills, register):
    """BASE plus each declared skill's tools, in a stable order."""
    extra = []
    for s in skills:
        for t in register.get(s) or []:
            if t not in extra:
                extra.append(t)
    return BASE + extra


def validate(spec, register, channels, existing):
    """A list of reasons the spec cannot become a role; empty when it can."""
    errs = []
    name = str(spec.get("name") or "")
    if not NAME.match(name):
        errs.append(f"name {name!r}: lowercase letters, digits and '-', 3-21 characters")
    elif name in existing or name in RESERVED:
        errs.append(f"role {name!r} exists or is reserved: changing a role is Mark's")
    if spec.get("model") not in MODELS:
        errs.append(f"model must be one of {sorted(MODELS)}")
    chans = spec.get("channels") or []
    if not chans or any(c not in channels for c in chans):
        errs.append(f"channels {chans}: at least one, and only existing channels "
                    f"(create one first with !channel)")
    unknown = [s for s in spec.get("skills") or [] if s not in register]
    if unknown:
        errs.append(f"skills {unknown} are not promoted skills in the register")
    c = spec.get("contract") or {}
    missing = [k for k, _ in FIELDS if not str(c.get(k) or "").strip()]
    if missing:
        errs.append(f"contract misses {missing}")
    for k, limit in (("mandate", 1200), ("prompt", 2500)):
        v = str(spec.get(k) or "").strip()
        if not v or len(v) > limit:
            errs.append(f"{k}: required, at most {limit} characters")
    return errs


def _flow(items):
    """An inline YAML list the handbook gate can read; patterns are quoted."""
    return "[" + ", ".join(f'"{i}"' if "(" in i else i for i in items) + "]"


def _quote(text):
    return "\n".join("> " + ln if ln.strip() else ">" for ln in text.strip().splitlines())


def render(spec, npub, register, today):
    """The handbook definition for a validated spec."""
    allow = tools_for(spec.get("skills") or [], register)
    deny = ["Write", "Edit"] + ([] if any(t.startswith("Bash") for t in allow) else ["Bash"])
    chans = spec["channels"]
    contract = "\n".join(f"- **{label}:** {str(spec['contract'][k]).strip()}"
                         for k, label in FIELDS)
    return f"""---
status: actief
last_reviewed: {today}
agent:
  naam: {spec['name']}
  npub: {npub}
  chat:
    model: {spec['model']}
    channels: {_flow(chans)}
    tools: {{ allow: {_flow(allow)}, deny: {_flow(deny)} }}
    skills: {_flow(spec.get('skills') or [])}
  executie: null
---

# {spec['name']}

## Mandate

{spec['mandate'].strip()}

Created by the factory on {today}, on odin's decision (ratatoskr change
odin-runs-the-factory). Closing this role, or changing its mandate or tools, is
Mark's.

## Contract

{contract}

## Chat facet (ratatoskr · {', '.join('#' + c for c in chans)})

{_quote(spec['prompt'])}

Channel scope: {', '.join('`#' + c + '`' for c in chans)}.

## Execution facet

None. {spec['name']} runs in chat only.
"""
