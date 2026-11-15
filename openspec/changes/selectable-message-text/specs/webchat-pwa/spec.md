## MODIFIED Requirements

### Requirement: Reply to a message

Every message in the app SHALL offer a reply action through a button. A long
press on the bubble SHALL NOT start a reply, because on a phone that is the
gesture for selecting text. While replying, the compose bar SHALL show the
parent's author and first line, with a way to cancel. A reply SHALL be sent as
a relay thread reply (`e` tag with the `reply` marker), and SHALL be shown with
a compact quote of its parent. A malformed parent id SHALL be refused by the
server with a reason, not sent as a plain message.

#### Scenario: Mark replies to an agent's message

- **WHEN** Mark presses reply on architect's message and sends "go ahead"
- **THEN** the relay stores the message with `["e", <architect's id>, "", "reply"]`
  and the app shows it with a quote of architect's message

#### Scenario: A bad parent id

- **WHEN** `/api/send` receives a `reply_to` that is not 64 hex characters
- **THEN** it answers 400 with the reason and sends nothing

#### Scenario: A long press selects instead of replying

- **WHEN** Mark presses and holds a message bubble on his phone
- **THEN** no reply starts, the focus stays where it was, and the platform's
  text selection is free to happen

## ADDED Requirements

### Requirement: Selectable message text with copy buttons on code

Message text SHALL be selectable and copyable with the platform's own
selection. Code in a message SHALL render as code: single- and double-backtick spans
and fenced blocks, with or without a language word. Every
non-empty code part SHALL have a copy button that copies exactly that code with
one tap, and it SHALL say why when it cannot copy. All message text SHALL go in
as text, never as markup.

While a selection is open in the message list, a poll SHALL NOT re-render the
list. The app SHALL show how many new messages wait, SHALL show them on a tap,
when the selection ends, or after at most 30 seconds, and SHALL NOT count them
as seen before they are shown. A waiting list SHALL only ever be shown in the
channel it was fetched for.

#### Scenario: Copy a token

- **WHEN** a message reads "Your token: `ghp_…`" and Mark taps the copy button
  next to it
- **THEN** the clipboard holds exactly `ghp_…`, without backticks

#### Scenario: The clipboard is refused

- **WHEN** the clipboard API and `execCommand('copy')` both fail
- **THEN** the code is selected for the native menu and a message says why

#### Scenario: A new message while selecting

- **WHEN** Mark has text selected and a new message arrives
- **THEN** the selection stays, a pill says "1 new message — tap to show", and
  the channel's unread state does not move until the message is shown

#### Scenario: A selection left open

- **WHEN** a selection stays open for more than 30 seconds while messages wait
- **THEN** the waiting messages are shown anyway

#### Scenario: Switching channel while a list waits

- **WHEN** messages wait in #alpha and Mark switches to #bravo, whose fetch fails
- **THEN** #alpha's messages never render under #bravo
