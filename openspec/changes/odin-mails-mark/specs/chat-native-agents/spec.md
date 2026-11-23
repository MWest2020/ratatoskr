## ADDED Requirements

### Requirement: A chat agent can mail Mark and nobody else

A chat agent whose handbook definition allows the Gmail connector's
`send_message` (and optionally `reply`) SHALL be able to send Mark a mail. The
listener SHALL enforce the recipient with a PreToolUse hook on every chat
turn, not with an instruction to the agent. The hook SHALL deny a Gmail call
unless it is `send_message` or `reply` whose `to` holds `mark@westerweel.work`
alone, with no cc, no bcc, no draft, no attachment, no reply-all and no input
field it does not know. It SHALL deny every other Gmail tool, and it SHALL deny
a call whose input it cannot read.

The listener SHALL NOT spawn a chat agent whose definition allows any Gmail
tool other than `send_message` and `reply`. It SHALL tell the agent about mail
in its system prompt, generated from the definition, and say nothing when the
definition does not allow it.

#### Scenario: Mark asks for a mail

- **WHEN** a definition allows `send_message` and the agent sends a mail with
  `to = ["mark@westerweel.work"]`
- **THEN** the hook lets it through and the allowlist decides, as for any tool

#### Scenario: A mail to anyone else

- **WHEN** the agent sends a mail to another address, to Mark and another
  address, or to Mark with a cc or bcc
- **THEN** the hook denies it with a reason, nothing is sent, and the denial is
  reported like any other

#### Scenario: Forward, trash or a draft

- **WHEN** the agent calls a Gmail tool to forward, trash, label, draft or
  delete, whatever its definition allows
- **THEN** the hook denies it

#### Scenario: A definition asks for more

- **WHEN** a definition allows a Gmail tool other than `send_message` and `reply`
- **THEN** the listener does not spawn that agent and says why
