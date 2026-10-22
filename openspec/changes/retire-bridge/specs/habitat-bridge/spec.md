## ADDED Requirements

### Requirement: One road from the chat to the cage

There SHALL be exactly one way for a chat message to start a habitat run: the
`!build` marker, which the listener checks (`agents/build.py`). No other script
in the repository SHALL dispatch habitat from a message.

#### Scenario: The old bridge is gone

- **WHEN** someone looks for a way to dispatch habitat from the chat
- **THEN** they find `!build` and its how-to, and no `orchestrator/bridge.py`
