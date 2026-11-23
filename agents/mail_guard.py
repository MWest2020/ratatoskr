# SPDX-License-Identifier: MIT
"""Mail to Mark, and to nobody else: the PreToolUse hook of every chat turn.

Mark, 2026-11-23: "en odin kan niet mailen net als jij, of weet niet hoe."
A chat agent may hold two tools of the claude.ai Gmail connector,
`send_message` and `reply`, through its handbook definition (change
odin-mails-mark). The allowlist cannot look at a tool's input, so this hook
does: it runs before every connector call of a chat turn and denies a Gmail
call unless it is one mail to Mark alone.

    to = [mark@westerweel.work]; no cc, no bcc; no draft, no attachment;
    a reply only with `to` set to Mark and never to all.

Every other Gmail tool (forward, trash, label, draft, delete, ...) is denied
here as well, whatever a definition allows. Fail-closed: input it cannot read
is a denial, not a pass. The hook is wired in by `providers.run` through
`--settings`, so it holds for every agent and every turn, not only odin's.

    echo '{"tool_name": ..., "tool_input": {...}}' | python3 agents/mail_guard.py
"""
import json
import os
import sys

MARK = "mark@westerweel.work"
SEND = "mcp__claude_ai_Gmail__send_message"
REPLY = "mcp__claude_ai_Gmail__reply"
TOOLS = (SEND, REPLY)
# Input fields a mail to Mark may carry. Anything else (draftId, attachments,
# whatever a new connector version adds) is a denial: a field nobody decided
# about could change where the mail goes or what leaves the host.
FIELDS = {
    SEND: {"to", "cc", "bcc", "subject", "body", "htmlBody", "includeSignature",
           "replyThreadId", "replyToMessageId"},
    REPLY: {"messageId", "to", "cc", "bcc", "body", "htmlBody", "includeSignature",
            "replyAll"},
}
# What the hook matches: every connector tool. The guard itself picks out the
# Gmail ones, also under another connector name (`mcp__claude_ai_Gmail_2__`).
MATCHER = "mcp__.*"


def is_gmail(tool):
    return str(tool).startswith("mcp__") and "gmail" in str(tool).lower()


def refusal(tool, inp):
    """The reason this call is denied, or "" when it is a mail to Mark alone
    (or not a Gmail call at all: then the allowlist decides, as before)."""
    if not is_gmail(tool):
        return ""
    if tool not in TOOLS:
        return f"{tool} is not allowed: a chat agent only sends Mark a mail or replies to him"
    if not isinstance(inp, dict):
        return "the call's input is not an object"
    extra = sorted(set(inp) - FIELDS[tool])
    if extra:
        return f"field(s) not allowed in a mail to Mark: {', '.join(extra)}"
    to = inp.get("to")
    if to is None and tool == REPLY:
        return "a reply must name its recipient: set to = [\"" + MARK + "\"]"
    if isinstance(to, str):
        to = [to]
    if not isinstance(to, list) or [str(a).strip().lower() for a in to] != [MARK]:
        return f"the only recipient allowed is {MARK}, alone in `to`"
    for field in ("cc", "bcc"):
        if inp.get(field) not in (None, [], ""):
            return f"no {field}: a mail goes to Mark alone"
    if inp.get("replyAll") not in (None, False):
        return "no reply-all: a reply goes to Mark alone"
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


def settings():
    """The `--settings` JSON that wires this hook into a turn. The interpreter
    is the listener's own, by absolute path: a hook whose command is not found
    is a non-blocking error in Claude Code, and the call would run."""
    cmd = f"{sys.executable} {os.path.abspath(__file__)}"
    return json.dumps({"hooks": {"PreToolUse": [
        {"matcher": MATCHER, "hooks": [{"type": "command", "command": cmd, "timeout": 10}]}]}})


def stray(allow):
    """Gmail tools in a definition other than send and reply. The listener
    refuses to spawn such an agent (bootstrap), as it does a free Bash."""
    return [t for t in allow or [] if is_gmail(str(t).split("(", 1)[0]) and t not in TOOLS]


def clause(cfg):
    """What the system prompt says about mail: only when the definition
    allows sending, so the announcement cannot drift from the mandate."""
    if SEND not in ((cfg or {}).get("allow") or []):
        return ""
    reply = (f" To answer in a thread of his, use `{REPLY}` with the message id and "
             f"to = [\"{MARK}\"]." if REPLY in cfg["allow"] else "")
    return ("\n\nYou can MAIL MARK, and only him: call "
            f"`{SEND}` with to = [\"{MARK}\"], a subject and an `htmlBody`.{reply} "
            "No cc, no bcc, no attachments, no drafts, no forwarding; anything else "
            "is refused by a hook. Load a tool's schema first with ToolSearch "
            f"(`select:{SEND}`) when it is only listed by name. Use it when Mark asks "
            "for a mail; say in the channel that you sent it.")


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
