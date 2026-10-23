## ADDED Requirements

### Requirement: A reply addresses the agent it replies to

When a human's message replies to an agent's message in the same channel, the
listener SHALL treat that agent as addressed, as an @mention does, within the
agent's channel scope. An explicit @mention SHALL take precedence. In a shared
room, a reply SHALL continue the issue referenced by the parent message.

#### Scenario: A reply without @

- **WHEN** Mark replies "go ahead" to bouwer's message in #bouw, without an @
- **THEN** bouwer answers, as if Mark had written "@bouwer go ahead"

#### Scenario: A reply in the room

- **WHEN** Mark replies to architect's message ending `· ratatoskr#57` in
  #werkplaats while #58 is the room's latest issue
- **THEN** the message is recorded on ratatoskr#57 and architect answers
