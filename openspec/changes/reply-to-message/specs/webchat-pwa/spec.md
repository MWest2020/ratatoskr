## ADDED Requirements

### Requirement: Reply to a message

Every message in the app SHALL offer a reply action: a button, and a long press
on the bubble. While replying, the compose bar SHALL show the parent's author
and first line, with a way to cancel. A reply SHALL be sent as a relay thread
reply (`e` tag with the `reply` marker), and SHALL be shown with a compact
quote of its parent. A malformed parent id SHALL be refused by the server with
a reason, not sent as a plain message.

#### Scenario: Mark replies to an agent's message

- **WHEN** Mark presses reply on architect's message and sends "go ahead"
- **THEN** the relay stores the message with `["e", <architect's id>, "", "reply"]`
  and the app shows it with a quote of architect's message

#### Scenario: A bad parent id

- **WHEN** `/api/send` receives a `reply_to` that is not 64 hex characters
- **THEN** it answers 400 with the reason and sends nothing
