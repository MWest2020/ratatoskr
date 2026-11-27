## ADDED Requirements

### Requirement: Images can be pasted or attached in the chat

The chat SHALL let the user paste or attach one image per message, with the
message text as its caption. Only PNG, JPEG and WebP SHALL be offered for
upload; SVG SHALL be refused. A preview SHALL be shown as an `<img>` from a
blob URL and never through `innerHTML`. A refusal SHALL show the reason, and
the image SHALL stay in the composer after a failed send.

#### Scenario: Paste a screenshot

- **WHEN** the user pastes a PNG into the input, types a caption and sends
- **THEN** one message with that caption and the image goes to the channel

#### Scenario: Refused type

- **WHEN** the user attaches an SVG
- **THEN** the app refuses it and says that the type is not accepted

#### Scenario: The server refuses

- **WHEN** the server refuses the image (size, dimension, metadata)
- **THEN** the composer shows the server's reason and keeps the image for a
  retry
