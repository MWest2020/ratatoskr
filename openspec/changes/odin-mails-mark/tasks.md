# Tasks

## 1. Decide
- [x] **Mark.** Build it. Mark, 2026-11-23, to the coding session: "en odin kan
      niet mailen net als jij, of weet niet hoe. Jarvis moet dit ook kunnen."
      Scope from the coding session: Mark is the only recipient, enforced in code.

## 2. Mail guard
- [x] `agents/mail_guard.py`: the recipient rule (plain ASCII, nothing around
      it), deny-by-default for every other Gmail tool including `reply`,
      fail-closed on unreadable input, and the `--settings` JSON with
      `disableAllHooks: false`, `env.CLAUDE_CODE_SHELL_PREFIX = ""` and
      `/usr/bin/timeout 8 <interpreter> -I <script> || exit 2`; threading via
      `replyThreadId` only.
- [x] `agents/test_mail_guard.py` covers the rule and the wiring:
      - a mail to Mark passes, threaded or not;
      - refused: another recipient, Mark plus another, lookalikes (Kelvin sign,
        no-break or em space), cc, bcc, a draft, an attachment, and the reply,
        forward, trash and label tools;
      - no mail is sent.
- [x] `agents/test_mail_guard_hook.py` runs the hook through a shell as Claude
      Code does: `disableAllHooks` is false, and a missing interpreter, a moved
      script, a crash and a hang each exit 2.

## 3. Listener
- [x] `providers.run` passes the hook on every turn.
- [x] `bootstrap.build_agents` refuses a definition with a sending connector
      tool other than Gmail send_message; `agent_skills.install` does not install
      a skill whose allowed-tools hold one.
- [x] The system prompt announces mail only when the definition allows it.
- [x] A seam test: definition → `build_agents` → `providers.run` → the command
      line carries the tool and the hook.
- [x] Checked live without sending anything. A `claude -p` turn tried a mail to
      `nobody@example.invalid`, once on a send tool that was not allowed and once
      through a fake MCP server that only logs. Each time the hook refused it.
      Refused with the fix, and let through without it (the control):
      - a working directory with `disableAllHooks: true`;
      - a missing interpreter.

      With the fix, a moved script and a hang were refused too.
- [x] `agents/turn_settings.py`: no turn while the listener tree's
      `.claude/settings*.json` holds a key outside the allow-list; reported in
      #escalatie. `agents/test_turn_settings.py`.
- [x] `agent_skills.allowed_tools` splits `allowed-tools` written as one
      string (commas or whitespace, not inside parentheses).
- [x] Re-review probes, run live with `claude -p` and the fake MCP server.
      Each one was let through by the previous hook and denied by the new one:
      - H: a project `env.PATH` with a fake `timeout`;
      - I: a project `env.CLAUDE_CODE_SHELL_PREFIX`;
      - K: the same prefix in `settings.local.json`.

      The listener check refuses all three directories before a turn starts. A
      project skill still loads with the new settings.
- [x] `verify.sh`: all unit tests green.

## 4. The mandate (Mark's gate)
- [x] A skill that declares the tool, because a role's tools follow from
      its skills: `mail-mark` in skill-forge, judged 0.92 and promoted, with the
      register regenerated (MWest2020/skill-forge#16).
- [ ] Handbook PR for `docs/agents/odin.md`: skill `mail-mark`, its tool
      in `allow`, a `mail_mark` capability, one line in the chat facet, and the
      register mirror (MWest2020/handbook#47). **Mark merges it after this change
      is deployed and skill-forge#16 is merged.** In the other order, odin gets the
      tools without the hook.

## 5. Proven live (after deploy, the handbook merge and a listener restart)
- [ ] "@odin mail me the open proposals" in #general: a mail arrives at
      mark@westerweel.work, and odin says so in the channel.
- [ ] "@odin mail the open proposals to someone@example.org": refused, the
      denial shows in #escalatie, nothing is sent.
- [ ] Archive this change.
