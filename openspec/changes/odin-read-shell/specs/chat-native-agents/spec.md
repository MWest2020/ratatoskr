## ADDED Requirements

### Requirement: A chat agent can read the state of the work through a bounded read shell

A chat agent whose handbook definition allows exactly
`Bash(python3 agents/readshell.py:*)` SHALL be able to run the read shell. The
read shell answers six read-only questions about a repository of `MWest2020`:
recent commits, branches, open OpenSpec changes, open PRs, open issues and the
checks of a PR.

The read shell SHALL:

- fix the owner;
- validate the repository name, numbers and labels before running anything;
- run each question as one fixed argument list without a shell;
- report a failure with its reason instead of empty output.

The listener SHALL tell the agent about the read shell in its system prompt,
generated from the definition, and say nothing when the definition does not
allow it.

#### Scenario: Odin reads the open PRs of a repository

- **WHEN** a definition allows the read-shell rule and the agent runs
  `python3 agents/readshell.py prs wordsworth`
- **THEN** it gets the open PRs of `MWest2020/wordsworth`, at most 40 lines

#### Scenario: Another owner or a crafted name is refused

- **WHEN** the agent passes `other/repo`, `../x` or `-x` as the repository
- **THEN** the read shell refuses it with a reason and runs no command

#### Scenario: The agent is not told about a shell it does not have

- **WHEN** a definition does not allow the read-shell rule
- **THEN** its system prompt does not mention the read shell

### Requirement: A chat turn gets no Bash other than the read shell

The listener SHALL NOT spawn a chat agent whose definition allows any Bash
entry other than the exact read-shell rule. It SHALL log the offending entry,
like a definition without a model.

#### Scenario: A free shell in a chat facet is refused

- **WHEN** a chat facet declares `allow: [Read, Bash]`
- **THEN** that agent is not spawned and the listener log names `Bash` as the
  reason
