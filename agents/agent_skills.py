# SPDX-License-Identifier: MIT
"""Phase 5 of odin-runs-the-factory: a chat agent's declared skills reach it.

Until 2026-10-23 a role's `skills:` was a declaration only. The turn allowed
Read/Grep/Glob and whatever its skills' tools were, but not the `Skill` tool,
so under `--permission-mode dontAsk` no skill could be invoked.

Two parts, both from the definition:

- **install**: at listener start, copy each declared skill from the skill-forge
  checkout into `<listener>/.claude/skills/<slug>/`, the project skills
  directory Claude Code reads from the turn's working directory. That
  directory is gitignored. A skill the register knows but the checkout lacks is
  logged, not guessed.
- **allow**: each agent's turn gets `Skill(<slug>)` for ITS declared skills
  only. The coding session's own skills in ~/.claude/skills stay out of reach,
  because dontAsk refuses every Skill(...) not on the list.
"""
import os
import re
import shutil

import yaml

import mail_guard

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SOURCE = os.path.expanduser("~/skill-forge/skills")


def allow_rules(skills):
    """`Skill(<slug>)` for each declared skill with a sane name."""
    return [f"Skill({s})" for s in skills or [] if SLUG.match(s)]


def install(agents, root, source=SOURCE, log=print):
    """Copy every skill some agent declares into `<root>/.claude/skills`.
    Returns {slug: "" or the reason it is missing}."""
    wanted = sorted({s for a in agents.values() for s in a.get("skills") or []
                     if SLUG.match(s)})
    dest = os.path.join(root, ".claude", "skills")
    os.makedirs(dest, exist_ok=True)
    result = {}
    for slug in wanted:
        src = os.path.join(source, slug)
        if not os.path.isfile(os.path.join(src, "SKILL.md")):
            result[slug] = f"no {slug}/SKILL.md in {source}"
            log(f"[listener] skill {slug}: {result[slug]}", flush=True)
            continue
        risky = mail_guard.stray(allowed_tools(os.path.join(src, "SKILL.md")))
        if risky:
            # A skill's allowed-tools are pre-approved while it runs: a sending
            # connector tool there would sidestep the definition (odin-mails-mark).
            result[slug] = f"allowed-tools that send ({risky}): not installed"
            log(f"[listener] skill {slug}: {result[slug]}", flush=True)
            continue
        target = os.path.join(dest, slug)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(src, target, ignore=shutil.ignore_patterns("iterations", "*.yml"))
        result[slug] = ""
    for stale in set(os.listdir(dest)) - set(wanted):   # no longer declared by anyone
        shutil.rmtree(os.path.join(dest, stale), ignore_errors=True)
    return result


def split_tools(text):
    """`allowed-tools` written as one string: names separated by commas or
    whitespace, except inside a rule's parentheses (`Bash(git log:*)`)."""
    out, word, depth = [], "", 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and (ch == "," or ch.isspace()):
            if word:
                out.append(word)
            word = ""
        else:
            word += ch
    return out + ([word] if word else [])


def allowed_tools(path):
    """A SKILL.md's `allowed-tools`, or ["<unreadable>"] when the front matter
    cannot be read: an unreadable skill is not installed (fail-closed)."""
    try:
        text = open(path, encoding="utf-8").read()
        meta = yaml.safe_load(text.split("---", 2)[1]) if text.startswith("---") else {}
        tools = (meta or {}).get("allowed-tools") or []
        if isinstance(tools, str):
            return split_tools(tools)
        return [t for item in tools for t in split_tools(str(item))]
    except Exception:
        return ["mcp__gmail__unreadable"]


def clause(skills):
    """The agent's own skills, named in its prompt, so it loads them instead of
    improvising (2026-10-23: odin had read-state and used the read shell bare)."""
    names = [s for s in skills or [] if SLUG.match(s)]
    if not names:
        return ""
    return ("\n\nYour SKILLS: " + ", ".join(f"`{n}`" for n in names) + ". Load the "
            "matching skill with the Skill tool before you do what it covers; it says "
            "how, and what its answers mean.")
