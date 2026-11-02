## ADDED Requirements

### Requirement: The listener delivers an attached image to the agent as a file

When a message carries an image reference, the listener SHALL fetch the file,
validate it again (type by magic bytes, size), write it to a per-turn scratch
directory, and give the agent the path in its prompt. The agent SHALL read it
through `Read(<dir>/**)`, and no new tool SHALL be granted. The directory SHALL
be removed after the turn.

#### Scenario: Agent reads the image

- **WHEN** Mark sends a screenshot to an agent whose model supports vision
- **THEN** the agent receives a path under the scratch directory and can read
  the image through `Read`

#### Scenario: Scratch is removed

- **WHEN** the turn ends
- **THEN** the scratch directory no longer exists

### Requirement: A failed image delivery is reported

When the listener cannot fetch or validate an image, it SHALL say in the
channel what failed and SHALL NOT run the turn as if the image were absent.

#### Scenario: File missing

- **WHEN** the referenced file cannot be fetched
- **THEN** the channel shows which image failed and why, and the agent does not
  answer as if there were no image
