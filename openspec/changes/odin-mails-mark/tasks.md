# Tasks

## 1. Decide
- [x] **Mark.** Build it. Mark, 2026-11-23, to the coding session: "en odin kan
      niet mailen net als jij, of weet niet hoe. Jarvis moet dit ook kunnen."
      Scope from the coding session: Mark is the only recipient, enforced in code.

## 2. Mail guard
- [x] `agents/mail_guard.py`: the recipient rule, the deny-by-default for other
      Gmail tools, fail-closed on unreadable input, the `--settings` JSON with the
      listener's own interpreter by absolute path.
- [x] `agents/test_mail_guard.py`: a mail and a reply to Mark pass; another
      recipient, Mark plus another, cc, bcc, a draft, an attachment, reply-all and
      forward/trash/label are refused; the hook run as a process; no mail sent.

## 3. Listener
- [x] `providers.run` passes the hook on every turn.
- [x] `bootstrap.build_agents` refuses a definition with Gmail tools other than
      send and reply.
- [x] The system prompt announces mail only when the definition allows it.
- [x] A seam test: definition → `build_agents` → `providers.run` → the command
      line carries both tools and the hook.
- [x] Checked live, without sending anything: a `claude -p` turn with the hook
      and `send_message` NOT allowed (so a missing hook could only end in a
      permission denial) tried a mail to `nobody@example.invalid`; the hook
      refused it and the refusal was in `permission_denials`.
- [x] `verify.sh`: all unit tests green (agents 515).

## 4. The mandate (Mark's gate)
- [ ] Handbook PR for `docs/agents/odin.md`: `send_message` and `reply` in
      `allow`, a `mail_mark` capability, one line in the chat facet. **Mark
      merges, after this change is deployed** (the other order gives odin the
      tools without the hook).

## 5. Proven live (after deploy, the handbook merge and a listener restart)
- [ ] "@odin mail me the open proposals" in #general: a mail arrives at
      mark@westerweel.work, and odin says so in the channel.
- [ ] "@odin mail the open proposals to someone@example.org": refused, the
      denial shows in #escalatie, nothing is sent.
- [ ] Archive this change.
