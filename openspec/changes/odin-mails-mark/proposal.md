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
  It denies a Gmail connector call unless it is `send_message` or `reply` with
  `to = ["mark@westerweel.work"]` alone: no cc, no bcc, no draft, no
  attachment, no reply-all, and no input field it does not know. Every other
  Gmail tool (forward, trash, label, draft, delete, read) is denied too. Input
  it cannot read is a denial. The allowlist cannot look at a tool's input; the
  hook can, and it is code, not a sentence in a prompt.
- **Two tools at most in a definition**: the listener refuses to spawn an agent
  whose chat facet allows any Gmail tool other than `send_message` and
  `reply`, as it refuses a free Bash.
- **The agent is told**: when its definition allows `send_message`, its system
  prompt says how to mail Mark and that nobody else can be mailed, generated
  from the definition (the read-shell pattern).
- **The mandate is Mark's**: odin gets the two tools through the skill
  `mail-mark` (skill-forge), which declares them, and through its handbook
  definition (`docs/agents/odin.md`), in a handbook PR that Mark merges. Until
  then this change is inert, apart from the hook, which only refuses.

## Out of scope

- Reading or searching mail. A reply needs a message id; odin replies when it
  has one (from Mark, or from its own send in the same turn). Reading Mark's
  inbox from a chat turn that posts in a channel is a separate decision.
- Mail to anyone else, ever.
