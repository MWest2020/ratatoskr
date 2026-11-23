## ADDED Requirements

### Requirement: A chat agent runs only with the system prompt from its definition

The listener SHALL take a chat agent's system prompt from the blockquote under
the `## Chat facet` heading of its handbook definition. The heading may be
written with a hyphen or a space, in any case. The listener SHALL NOT spawn an
agent whose prompt comes out empty, and SHALL log the reason, as it does for a
definition without a model.

#### Scenario: The translated heading is found

- **WHEN** a definition has `## Chat facet (ratatoskr · #bouw)` followed by a
  prose line and a blockquote
- **THEN** the system prompt is the blockquote, without the prose line and
  without the next section

#### Scenario: An empty prompt does not run

- **WHEN** a definition has no blockquote under its chat facet
- **THEN** that agent is not spawned and the listener log says
  `no system prompt`

### Requirement: The role contract reaches the model

When a definition has a `## Contract` section, the listener SHALL append that
section to the agent's system prompt, after one instruction line. The line
says: answer only what the contract says you take, and for anything under "Not
mine", name whose it is and stop. A definition without a contract SHALL keep
its prompt unchanged, and a contract SHALL NOT count as a prompt when the chat
facet has none.

#### Scenario: The contract follows the prompt

- **WHEN** a definition has a chat facet with a blockquote and a `## Contract`
  section
- **THEN** the system prompt is the blockquote, then the instruction line, then
  the contract

#### Scenario: No contract, no change

- **WHEN** a definition has no `## Contract` section
- **THEN** its system prompt is exactly the blockquote
