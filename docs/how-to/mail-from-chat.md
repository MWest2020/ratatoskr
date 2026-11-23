---
status: current
last_reviewed: 2026-11-23
---

# Let a chat agent mail Mark

A chat agent can send Mark a mail through the claude.ai Gmail connector, which
every Claude process on the host sees. It can mail **Mark and nobody else**
(change `odin-mails-mark`). The limit is code, in two places:

- **The mail guard** (`agents/mail_guard.py`) is a PreToolUse hook that
  `providers.run` passes to every chat turn with `--settings`, whatever the
  agent's allowlist. It lets a Gmail call through only when it is
  `mcp__claude_ai_Gmail__send_message` with `to = ["mark@westerweel.work"]`
  alone, in plain ASCII with nothing around it. Threading goes through
  `replyThreadId` on that same send. It denies:
  - a cc or bcc;
  - a draft (`draftId`);
  - an attachment;
  - any input field it does not know, `replyToMessageId` included (it needs
    the connector's read access, and what the server does with it cannot be
    checked without sending);
  - every other Gmail tool, `reply` included. The connector's reply may copy
    a thread's default cc recipients, which the call does not show. Forward,
    trash, label, draft, delete and read are denied too.

  Input it cannot read is a denial.
- **The hook cannot be switched off, wrapped or fail open.**
  - Its settings carry `"disableAllHooks": false` and
    `"env": {"CLAUDE_CODE_SHELL_PREFIX": ""}`, and command-line settings beat a
    project's or the user's `.claude/settings.json`.
  - The command is `/usr/bin/timeout 8 <interpreter> -I mail_guard.py || exit 2`.
    Every program is named by absolute path, so a project's `env.PATH` picks
    nothing. Python runs isolated, ignoring `PYTHON*` variables. A missing
    interpreter or `timeout`, a moved file, a crash or a hang all exit 2, which
    blocks the call.
- **The listener tree's own settings are checked before every turn**
  (`agents/turn_settings.py`, after jarvis' `checkout_settings`). The
  listener runs no turn when its working directory's
  `.claude/settings.json` or `settings.local.json`:
  - holds a key outside a small allow-list (`$schema`, `model`,
    `includeCoAuthoredBy`, `cleanupPeriodDays`, `outputStyle`, `permissions`
    with only `deny` and `ask`);
  - is a symlink;
  - cannot be read as a JSON object;

  or while a project `.mcp.json` exists there, in any form. `claude -p` starts a
  project's MCP servers without asking, and their command runs at turn start,
  beside the hook. `--strict-mcp-config` is no way out, because it also drops the
  claude.ai Gmail connector.

  The check runs again after the turn, and a file that appeared during the turn
  is reported in #escalatie as `unsafe settings after the turn`.

  That covers `env` (`PATH`, `LD_PRELOAD`, `BASH_ENV`, a shell prefix), `hooks`,
  helpers and MCP servers. The refusal goes to #escalatie with the file and the
  key. It is not done with `--setting-sources user`, because that would also stop
  the listener's `.claude/skills` from loading.
- **The listener** refuses to start an agent whose definition allows a sending
  connector tool other than Gmail `send_message`, and logs `sending connector
  tools other than Gmail send_message`. That covers any other Gmail tool and
  any `mcp__` tool whose name says send, reply, forward, draft or mail. It does
  not install a skill whose `allowed-tools` holds one either.

A denial comes back to the agent with the reason, and shows up in #escalatie
like every permission denial.

## Giving it to an agent

A role's tools follow from its skills. The skill `mail-mark` (skill-forge)
declares the tool and tells the agent how to use it. Both the skill and
its tools go in the chat facet of the agent's handbook definition
(`docs/agents/`, which the owner merges):

```yaml
chat:
  tools: { allow: [Read, Grep, Glob, mcp__claude_ai_Gmail__send_message],
           deny: [Write, Edit] }
  skills: [mail-mark]
``` When the
definition allows `send_message`, the system prompt gets a paragraph saying how
to mail Mark and that nobody else can be mailed. Without it, nothing.

**Deploy this repository first, then merge the handbook change.** The other
order gives the agent the tools on a listener that does not pass the hook yet.
After the merge, check the definition with the listener's own fetch (see
[read shell](read-shell.md#giving-it-to-an-agent) for why curl is not enough)
and restart:

    python3 -c 'import sys; sys.path.insert(0, "agents"); import bootstrap, mail_guard
    d = bootstrap.fetch_def("https://raw.githubusercontent.com/MWest2020/handbook/main/docs/agents", "odin")
    print(mail_guard.SEND in d["allow"], mail_guard.stray(d["allow"]))'

Expect `True []`.

## Checking the guard

Judge a call without sending anything:

    echo '{"tool_name":"mcp__claude_ai_Gmail__send_message","tool_input":{"to":["x@example.org"]}}' \
      | python3 agents/mail_guard.py

A denial prints a JSON object with `"permissionDecision": "deny"`; a mail to
Mark alone prints nothing.

## When it goes wrong

- **#escalatie says "unsafe settings: …/.claude/settings.json sets env".** A
  settings file appeared in the listener tree (a `git pull` brings one without
  anyone editing it). Remove the key it names; no turn runs until then.
- **The agent says it has no mail tool.** The definition does not allow
  `send_message`, or the listener was not restarted after the handbook merge.
- **A refusal from "the mail guard".** The call had another recipient, a cc,
  a bcc, a draft or an attachment. That is the boundary working.
- **A reply is refused.** The `reply` tool is never allowed. The agent sends a
  new mail to Mark with `replyThreadId` to thread it.
