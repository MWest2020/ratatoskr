## ADDED Requirements

### Requirement: A chat agent can mail Mark and nobody else

A chat agent whose handbook definition allows the Gmail connector's
`send_message` SHALL be able to send Mark a mail. The listener SHALL enforce
the recipient with a PreToolUse hook on every chat turn, not with an
instruction to the agent. The hook SHALL deny a Gmail call unless it is
`send_message` whose `to` holds `mark@westerweel.work` alone, in plain ASCII
with nothing around it, with no cc, no bcc, no draft, no attachment and no
input field it does not know. It SHALL deny every other Gmail tool, including
`reply`, and it SHALL deny a call whose input it cannot read.

The hook SHALL NOT be switched off or wrapped by a project's or the user's
settings, it SHALL run its programs by absolute path, and every failure to run
it (a missing interpreter or file, a crash, a timeout) SHALL block the call.
The listener SHALL NOT start a turn while its working directory's project
settings hold a key outside a fixed allow-list or a project `.mcp.json` exists,
SHALL report that refusal like any other, and SHALL check again after the turn
and report a file that appeared during it.

The listener SHALL NOT spawn a chat agent whose definition allows a sending
connector tool other than Gmail `send_message`, and SHALL NOT install a skill
whose allowed tools hold one. It SHALL tell the agent about mail in its system
prompt, generated from the definition, and say nothing when the definition
does not allow it.

#### Scenario: Mark asks for a mail

- **WHEN** a definition allows `send_message` and the agent sends a mail with
  `to = ["mark@westerweel.work"]`, optionally threaded with `replyThreadId`
  (`replyToMessageId` is refused)
- **THEN** the hook lets it through and the allowlist decides, as for any tool

#### Scenario: A mail to anyone else

- **WHEN** the agent sends a mail to another address, to Mark and another
  address, to a lookalike of Mark's address, or to Mark with a cc or bcc
- **THEN** the hook denies it with a reason, nothing is sent, and the denial is
  reported like any other

#### Scenario: Reply, forward, trash or a draft

- **WHEN** the agent calls a Gmail tool to reply, forward, trash, label, draft
  or delete, whatever its definition allows
- **THEN** the hook denies it

#### Scenario: Hooks switched off in a settings file

- **WHEN** the turn's working directory or the user's settings carry
  `disableAllHooks: true`
- **THEN** the hook still runs and denies a mail to anyone but Mark

#### Scenario: A project settings file in the listener tree

- **WHEN** the listener's working directory has a `.claude/settings.json` or
  `settings.local.json` with `env` (such as `PATH` or
  `CLAUDE_CODE_SHELL_PREFIX`), `hooks` or another key outside the allow-list
- **THEN** no turn starts, and #escalatie names the file and the key

#### Scenario: A project MCP server in the listener tree

- **WHEN** the listener's working directory has a `.mcp.json`
- **THEN** no turn starts, and no server command from it runs

#### Scenario: The hook cannot run

- **WHEN** the hook's interpreter or script is missing, the script crashes, or
  it runs past its deadline
- **THEN** the call is blocked

#### Scenario: A definition or a skill asks for more

- **WHEN** a definition or a skill's allowed tools hold a sending connector
  tool other than Gmail `send_message`
- **THEN** the listener does not spawn that agent, or does not install that
  skill, and says why
