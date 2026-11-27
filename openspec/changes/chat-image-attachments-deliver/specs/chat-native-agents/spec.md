## ADDED Requirements

### Requirement: The listener delivers an image in Mark's message to the agent as a file

When the message that starts a turn is Mark's own, checked by pubkey, and
carries an image reference, the listener SHALL fetch the image from the
relay's media store, check it again (type by magic bytes, size, and its hash
against the reference), write it to a per-turn scratch directory and give the
agent its path in the prompt. The agent SHALL read it through the `Read` grant
it already has; no new tool SHALL be granted. The directory SHALL be removed
when the turn ends, however it ends. The listener SHALL NOT fetch an image
referenced in a message by any other identity.

#### Scenario: Agent reads the image

- **WHEN** Mark sends a screenshot to an agent whose model supports vision
- **THEN** the agent receives a path under the scratch directory and reads
  the image through `Read`

#### Scenario: Scratch is removed

- **WHEN** the turn ends, also by a timeout or an error
- **THEN** the scratch directory no longer exists

#### Scenario: Not from an agent

- **WHEN** a message by an agent identity carries an image reference
- **THEN** the listener fetches nothing

### Requirement: A failed image delivery is reported

When the listener cannot fetch or validate an image, it SHALL say in the
channel which image failed and why, and SHALL NOT run the turn as if the image
were absent.

#### Scenario: Image expired

- **WHEN** the relay no longer has the referenced image
- **THEN** the channel shows that the image expired, and the agent does not
  answer as if there were no image
