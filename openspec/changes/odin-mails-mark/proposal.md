# Odin mails Mark, and only Mark

## Why

Mark, 2026-11-23: *"en odin kan niet mailen net als jij, of weet niet hoe."*
That day, on "@odin mail de openstaande proposals", odin answered
"LIMIT: I have no mail tool". The claude.ai Gmail connector is visible to every
Claude process on the host; it is simply not on odin's allowlist, and odin is
not told it exists. The coding session mails Mark with it every day.

Mark asked for it directly, so this change is built in the same PR; the PR is
the approval point.

## What changes

- **A mail guard** (`agents/mail_guard.py`): a PreToolUse hook that every chat
  turn gets through `--settings` in `providers.run`, whatever its allowlist.
  It denies a Gmail connector call unless it is `send_message` with
  `to = ["mark@westerweel.work"]` alone: plain ASCII with nothing around it,
  no cc, no bcc, no draft, no attachment, and no input field it does not
  know. Threading goes through `replyThreadId` or `replyToMessageId` on that
  same send. Every other Gmail tool is denied too, `reply` included, because
  it may copy a thread's default cc recipients and the call does not show
  them. So are forward, trash, label, draft, delete and read. The allowlist
  cannot look at a tool's input; the hook can, and it is code, not a sentence
  in a prompt.
- **The hook cannot be switched off or fail open.** The `--settings` JSON
  carries `"disableAllHooks": false`. Settings given on the command line beat
  a project's or the user's `.claude/settings.json`. The hook command is
  `timeout 8 <interpreter> <script> || exit 2` with a 10 s hook timeout. A
  missing interpreter, a moved file, a crash or a hang all end in exit 2,
  which Claude Code treats as a block. Any other failure would be a
  non-blocking error, and the call would run. Input the guard cannot read is a
  denial.
- **One sending tool at most, in a definition and in a skill**: the listener
  refuses to spawn an agent whose chat facet allows any sending connector tool
  other than Gmail `send_message`. That means any other Gmail tool, and any
  `mcp__` tool whose name says send, reply, forward, draft or mail. For the
  same reason it does not install a skill whose `allowed-tools` holds one,
  because a skill's allowed tools are pre-approved while it runs.
- **The agent is told**: when its definition allows `send_message`, its system
  prompt says how to mail Mark and that nobody else can be mailed, generated
  from the definition (the read-shell pattern).
- **The mandate is Mark's**: odin gets the tool through the skill `mail-mark`
  (skill-forge), which declares it, and through its handbook definition
  (`docs/agents/odin.md`), in a handbook PR that Mark merges. Until then this
  change is inert, apart from the hook, which only refuses.

## Out of scope

- Reading or searching mail. Threading needs a thread or message id; odin
  threads when it has one (from Mark, or from its own send in the same turn). Reading Mark's
  inbox from a chat turn that posts in a channel is a separate decision.
- Mail to anyone else, ever.
