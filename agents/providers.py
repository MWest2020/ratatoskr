# SPDX-License-Identifier: MIT
"""Provider seam: the agent backend sits behind one function. Separate from
listener.py so that file stays under the ≤200-line convention. Today 'claude-p'
(subscription first); a new backend = one extra branch. The handbook def
declares provider, model and tools (front matter agent.chat), and those are
enforced here — not merely declared (Mark, 2026-09-06: "afdwingen, niet yolo
free for all").
"""
import json
import os
import subprocess
import time

CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
# Three minutes. Mark, 2026-09-18: "in 3 minuten moet er gereviewed kunnen
# worden [...] als dat niet werkt, de timeout limits ophogen (of beide,
# helemaal goed)". It was 150 s. Splitting stays the first advice when a turn
# runs out (reporting.py); this is the "both".
MAX_TURN_S = 180

# What the agent subprocess is allowed to see of the environment. The listener
# carries the nsec of EVERY agent in its own environment; without this filter
# each turn inherits those keys (and the age key, GitHub token, ssh-agent) and
# one successful prompt injection is enough to read them through
# /proc/self/environ and post them in the channel.
ENV_KEEP = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TERM",
            "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME")

# Path tools are bounded to the work tree. `--allowedTools Read` on its own
# bounds NOTHING: verified 2026-09-06 that an agent read a file outside the repo
# with it and got no denial; with `Read(./**)` that same attempt is refused and
# reported.
PATH_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "NotebookEdit"}


# Only these three may get a second path: reading outside the work tree is
# sometimes needed (a skill-forge judgement about a clip in the zettelkast),
# writing outside it never is.
READ_TOOLS = ("Read", "Grep", "Glob")


def scoped(tools, extra=None, root=None):
    """Path tools get a work-tree scope; the rest stays as it is. With `root`
    the scope is absolute, so a session that runs `cd` keeps its permits
    (2026-10-24: a relative `./**` follows the session's current directory).

    `extra` = explicitly declared EXTRA read paths (per session type in
    sessions.yml). Every path becomes its own, equally tight scope — not a
    widening of the work-tree scope, but a second permit beside it."""
    base = f"/{os.path.normpath(root)}" if root else "."
    out = [f"{t}({base}/**)" if t in PATH_TOOLS else t for t in (tools or [])]
    for path in (extra or []):
        out += [f"{t}({path.rstrip('/')}/**)" for t in READ_TOOLS if t in (tools or [])]
    return out


def _target(inp):
    """The interesting part of a tool call, short: a path or a command."""
    for k in ("file_path", "path", "pattern", "command", "url"):
        v = inp.get(k)
        if v:
            v = str(v)
            return (v[-48:] if len(v) > 48 else v)
    return ""


def agent_env():
    """Only what the CLI needs — no keys, no tokens."""
    return {k: v for k, v in os.environ.items() if k in ENV_KEEP}


def main_model(usage, requested=None):
    """The model that did the WORK, from `modelUsage`.

    This used to take the first key of that map. A run can touch several models,
    and then the stats line named an arbitrary one — precisely the number you
    would read to see whether the declared model is enforced. Now: the model with
    the most tokens. No usage → whatever was requested."""
    if not isinstance(usage, dict) or not usage:
        return requested or ""

    def tokens(v):
        if not isinstance(v, dict):
            return 0
        return sum(x for k, x in v.items()
                   if isinstance(x, (int, float)) and "oken" in k)

    return max(usage, key=lambda k: tokens(usage[k]))


def model_matches(requested, actual):
    """Is the model that ran the family that was requested? The def names the
    intent (haiku/sonnet/opus), the run an exact id (claude-sonnet-5)."""
    if not requested:
        return True
    return requested.lower() in (actual or "").lower()


def run(provider, system, prompt, model=None, allow=None, deny=None, progress=None,
        no_tools=False, env=None):
    """Run one turn. Returns {answer, model, cost, turns, denials, error}.

    `denials` = the tool calls the permission layer refused; the listener reports
    those per run in #escalatie so a human decides whether the role should be
    widened. Without this field an agent would silently be able to do less than
    its mandate promises.
    """
    if provider not in (None, "claude-p", "claude"):
        return {"answer": f"(provider '{provider}' nog niet ondersteund door deze listener)",
                "model": "", "cost": 0.0, "turns": 0, "denials": [], "error": "provider"}

    # dontAsk = deny by default: anything outside --allowedTools is refused
    # instead of offered. Without this flag the agent kept tools like Agent,
    # WebFetch and SendMessage — the allowlist only decided what was allowed
    # WITHOUT asking. Measured 2026-09-06: with the flag a WebFetch attempt comes
    # back as a permission_denial, so #escalatie gets a machine signal and not
    # only self-reporting.
    cmd = [CLAUDE, "-p", "--output-format", "json", "--permission-mode", "dontAsk",
           "--append-system-prompt", system]
    if model:
        cmd += ["--model", model]
    if allow:
        cmd += ["--allowedTools", ",".join(scoped(allow))]
    if deny:
        cmd += ["--disallowedTools", ",".join(deny)]
    if no_tools:  # a classification, not an agent: no tool exists at all
        cmd += ["--tools", ""]
    # Prompt over stdin, not as an argument: --allowedTools/--disallowedTools are
    # variadic (`<tools...>`) and swallow a following positional argument ("Input
    # must be provided either through stdin or as a prompt argument").
    # Streaming instead of waiting: with stream-json every step arrives as it
    # happens, so the listener can show WHAT the agent is doing instead of ninety
    # seconds of silence. `progress` gets short lines ("Read providers.py").
    cmd += ["--output-format", "stream-json", "--verbose"]
    t0 = time.time()
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                env=env if env is not None else agent_env())
    except OSError as e:
        return {"answer": f"(kan {CLAUDE} niet starten)", "model": model or "", "cost": 0.0,
                "turns": 0, "denials": [], "error": str(e)[:120]}
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except BrokenPipeError:
        pass

    d, used, skills_used = {}, {}, []
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
        elif ev.get("type") == "assistant":
            for c in (ev.get("message") or {}).get("content", []):
                if c.get("type") == "tool_use":
                    used[c.get("name")] = used.get(c.get("name"), 0) + 1   # activity.py
                    if c.get("name") == "Skill":
                        skills_used.append(str((c.get("input") or {}).get("skill")))
                    if progress:
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
            "tools": used, "skills_used": skills_used,
            "error": "" if not d.get("is_error") else str(d.get("subtype") or "error")}
