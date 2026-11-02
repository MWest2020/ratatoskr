## ADDED Requirements

### Requirement: Images can be pasted or attached in the chat

The chat SHALL let the user paste or attach up to 3 images per message. Only
PNG, JPEG and WebP SHALL be accepted; SVG SHALL be refused. Images SHALL be
shown with `<img>` from a blob or same-origin URL and never through
`innerHTML`.

#### Scenario: Paste a screenshot

- **WHEN** the user pastes a PNG into the input and sends
- **THEN** the message goes out with a reference to the image and the image is
  shown in the chat

#### Scenario: Refused type

- **WHEN** the user attaches an SVG
- **THEN** the app refuses it and says that the type is not accepted

### Requirement: Uploads are gated, bounded and checked on the server

`POST /api/upload` SHALL require the session and the session token that
`/api/send` requires. It SHALL accept at most 5 MiB per image, decide the type
by magic bytes and not by the Content-Type header, strip EXIF, and store the
file under its content hash. A refused upload SHALL return an error that names
the reason.

#### Scenario: No session token

- **WHEN** an upload arrives without a valid session token
- **THEN** it is refused and nothing is stored

#### Scenario: Wrong type behind a right header

- **WHEN** a file with an `image/png` Content-Type has the magic bytes of
  another type
- **THEN** it is refused with the reason

#### Scenario: Too large

- **WHEN** an image is over 5 MiB
- **THEN** the upload is refused and the user sees the size limit, not a
  truncated image

### Requirement: The message carries a reference, not the image

A message with images SHALL carry only a reference to each stored image. The
image bytes SHALL NOT travel through the relay.

#### Scenario: Audit stays small

- **WHEN** a message with an image is sent
- **THEN** the relay event, the audit JSONL and the git mirror contain the
  reference and no image bytes
