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
        target = os.path.join(dest, slug)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(src, target, ignore=shutil.ignore_patterns("iterations", "*.yml"))
        result[slug] = ""
    for stale in set(os.listdir(dest)) - set(wanted):   # no longer declared by anyone
        shutil.rmtree(os.path.join(dest, stale), ignore_errors=True)
    return result


def clause(skills):
    """The agent's own skills, named in its prompt, so it loads them instead of
    improvising (2026-10-23: odin had read-state and used the read shell bare)."""
    names = [s for s in skills or [] if SLUG.match(s)]
    if not names:
        return ""
    return ("\n\nYour SKILLS: " + ", ".join(f"`{n}`" for n in names) + ". Load the "
            "matching skill with the Skill tool before you do what it covers; it says "
            "how, and what its answers mean.")
