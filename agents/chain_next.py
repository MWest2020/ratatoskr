# SPDX-License-Identifier: MIT
"""Pure parser for the chain-after-merge grammar in a change's `proposal.md`
(openspec change `chain-next-step-after-merge`).

A section is a level-2 heading (`## <Name>`, compared case-insensitively,
surrounding whitespace ignored) up to the next `## ` line or the end of the
file; only the first section of each name counts. Lines inside a fenced code
block (```) are never read as a heading and never scanned for an id, so an
example fence cannot be mistaken for the real grammar.
"""
import re

ID = re.compile(r"`([a-z0-9][a-z0-9-]*)`")
HEADING = re.compile(r"^##\s+(.+?)\s*$")


def _sections(text):
    sections, name, body, fenced = {}, None, [], False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            if name is not None:
                body.append(line)
            continue
        m = None if fenced else HEADING.match(line)
        if m:
            if name is not None and name not in sections:
                sections[name] = "\n".join(body)
            name, body = m.group(1).strip().lower(), []
            continue
        if name is not None:
            body.append(line)
    if name is not None and name not in sections:
        sections[name] = "\n".join(body)
    return sections


def parse(text):
    """{"next": id or None, "parents": [ids], "precondition": bool, "malformed": bool}."""
    sections = _sections(text)
    next_id, malformed = None, False
    if "next" in sections:
        m = ID.search(sections["next"])
        if m:
            next_id = m.group(1)
        else:
            malformed = True
    return {"next": next_id, "parents": ID.findall(sections.get("depends on", "")),
            "precondition": "deploy precondition" in sections, "malformed": malformed}
