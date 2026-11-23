# SPDX-License-Identifier: MIT
"""Mail to Mark, and to nobody else: the PreToolUse hook of every chat turn.

Mark, 2026-11-23: "en odin kan niet mailen net als jij, of weet niet hoe."
A chat agent may hold ONE tool of the claude.ai Gmail connector,
`send_message`, through its handbook definition (change odin-mails-mark). The
allowlist cannot look at a tool's input, so this hook does: it runs before
every connector call of a chat turn and denies a Gmail call unless it is one
mail to Mark alone.

    to = [mark@westerweel.work]; no cc, no bcc; no draft, no attachment.

Threading goes through `replyThreadId` / `replyToMessageId` on that same send.
The connector's `reply` is denied like every other Gmail tool: it may copy a
thread's default cc recipients, which the call does not show. Fail-closed:
input it cannot read is a denial; a hook that cannot run (no interpreter, a
crash, a timeout) exits 2, which blocks the call (`settings`).

    echo '{"tool_name": ..., "tool_input": {...}}' | python3 agents/mail_guard.py
"""
import json
import os
import shlex
import sys

MARK = "mark@westerweel.work"
SEND = "mcp__claude_ai_Gmail__send_message"
TOOLS = (SEND,)
# Input fields a mail to Mark may carry. Anything else (draftId, attachments,
# whatever a new connector version adds) is a denial: a field nobody decided
# about could change where the mail goes or what leaves the host.
FIELDS = {SEND: {"to", "cc", "bcc", "subject", "body", "htmlBody", "includeSignature",
                 "replyThreadId", "replyToMessageId"}}
# What the hook matches: every connector tool. The guard itself picks out the
# Gmail ones, also under another connector name (`mcp__claude_ai_Gmail_2__`).
MATCHER = "mcp__.*"
# The hook's own deadline, under Claude Code's (HOOK_TIMEOUT_S): a hook that
# Claude Code times out is a non-blocking error; one that `timeout` stops
# exits 124, and `|| exit 2` turns that into a block.
LIMIT_S = 8
HOOK_TIMEOUT_S = 10
# Words in a connector tool's name that mean it sends something on its own.
SENDING = ("send", "reply", "forward", "draft", "mail")


def is_gmail(tool):
    return str(tool).startswith("mcp__") and "gmail" in str(tool).lower()


def is_mark(address):
    """Exactly Mark's address: plain ASCII, nothing around it, any case. A
    Kelvin sign or a no-break space must not pass for a letter or nothing."""
    return (isinstance(address, str) and address.isascii()
            and address == address.strip() and address.lower() == MARK)


def refusal(tool, inp):
    """The reason this call is denied, or "" when it is a mail to Mark alone
    (or not a Gmail call at all: then the allowlist decides, as before)."""
    if not is_gmail(tool):
        return ""
    if tool not in TOOLS:
        return f"{tool} is not allowed: a chat agent only sends Mark a mail with {SEND}"
    if not isinstance(inp, dict):
        return "the call's input is not an object"
    extra = sorted(set(inp) - FIELDS[tool])
    if extra:
        return f"field(s) not allowed in a mail to Mark: {', '.join(extra)}"
    to = inp.get("to")
    if isinstance(to, str):
        to = [to]
    if not isinstance(to, list) or len(to) != 1 or not is_mark(to[0]):
        return f"the only recipient allowed is {MARK}, alone in `to`"
    for field in ("cc", "bcc"):
        if inp.get(field) not in (None, [], ""):
            return f"no {field}: a mail goes to Mark alone"
    return ""


def decision(payload):
    """The hook's stdout for one call: a deny object, or None to stay silent."""
    try:
        why = refusal(payload.get("tool_name", ""), payload.get("tool_input"))
    except Exception as e:  # fail-closed
        why = f"mail guard could not judge the call: {e}"
    if not why:
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"Refused by the mail guard: {why}. "
                                    f"Mail goes to {MARK} only (agents/mail_guard.py)."}}


def command(python=None, script=None, limit=LIMIT_S):
    """The hook's shell command. Every way it can fail to judge (interpreter
    or file missing, a crash, a hang) ends in exit 2, which Claude Code treats
    as a block; any other failure would be a non-blocking error, and the call
    would run."""
    python = python or sys.executable
    script = script or os.path.abspath(__file__)
    return f"timeout {limit} {shlex.quote(python)} {shlex.quote(script)} || exit 2"


def settings():
    """The `--settings` JSON that wires this hook into a turn. Settings given
    on the command line win over the user's and the project's, so a
    `disableAllHooks: true` in `.claude/settings.json` cannot switch it off."""
    return json.dumps({"disableAllHooks": False, "hooks": {"PreToolUse": [
        {"matcher": MATCHER, "hooks": [
            {"type": "command", "command": command(), "timeout": HOOK_TIMEOUT_S}]}]}})


def stray(tools):
    """Connector tools in a definition (or a skill's allowed-tools) that send
    something, other than Gmail send_message: any other Gmail tool, and any
    `mcp__` tool whose name says send, reply, forward, draft or mail. The
    listener refuses to spawn such an agent (bootstrap) and does not install
    such a skill (agent_skills), as it refuses a free Bash."""
    out = []
    for t in tools or []:
        name = str(t).split("(", 1)[0].strip()
        risky = is_gmail(name) or (name.startswith("mcp__")
                                   and any(w in name.lower() for w in SENDING))
        if risky and t != SEND:
            out.append(t)
    return out


def clause(cfg):
    """What the system prompt says about mail: only when the definition
    allows sending, so the announcement cannot drift from the mandate."""
    if SEND not in ((cfg or {}).get("allow") or []):
        return ""
    return ("\n\nYou can MAIL MARK, and only him: call "
            f"`{SEND}` with to = [\"{MARK}\"], a subject and an `htmlBody`. To "
            "answer in a thread of his, add `replyThreadId` (or `replyToMessageId`) "
            "to that same call. No cc, no bcc, no attachments, no drafts, no reply "
            "or forward tool; anything else is refused by a hook. Load the tool's "
            f"schema first with ToolSearch (`select:{SEND}`) when it is only listed "
            "by name. Use it when Mark asks for a mail; say in the channel that you "
            "sent it.")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as e:  # unreadable input: deny, never pass
        payload = {"tool_name": "mcp__gmail__unreadable", "tool_input": None}
        print(f"mail guard: unreadable hook input: {e}", file=sys.stderr)
    out = decision(payload if isinstance(payload, dict) else {"tool_name": "mcp__gmail__?"})
    if out:
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
