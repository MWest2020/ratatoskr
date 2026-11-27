## ADDED Requirements

### Requirement: An uploaded image is checked on the server and sent through the relay

`POST /api/upload` SHALL require the session and the session token that
`/api/send` requires, and SHALL check both before it reads the body. It SHALL
accept one image per request, at most 5 MiB, decide the type by magic bytes and
not by the Content-Type header, and accept only PNG, JPEG and WebP. It SHALL
remove the image's metadata with the same helper agents use, and refuse an
image that helper cannot strip without changing its pixels. It SHALL then send
one message to the channel, signed by the session's identity, with the caption
as text and the image attached through the relay's media store. The relay
event SHALL carry a reference to the image, not its bytes.

#### Scenario: No session token

- **WHEN** an upload arrives without a valid session token
- **THEN** it is refused before the body is read and no message is sent

#### Scenario: Wrong type behind a right header

- **WHEN** a file with an `image/png` Content-Type has the magic bytes of
  another type
- **THEN** it is refused with the reason and no message is sent

#### Scenario: Too large

- **WHEN** an upload is over 5 MiB
- **THEN** it is refused with the size limit, nothing is truncated and no
  message is sent

#### Scenario: Metadata does not leave the chat

- **WHEN** a JPEG carrying EXIF and a comment is uploaded
- **THEN** the image the relay stores holds neither, and its pixel data is
  unchanged

#### Scenario: One message, signed, with a reference

- **WHEN** a valid image is uploaded with a caption to a channel
- **THEN** one message appears in that channel from the session's identity,
  its text is the caption, its event carries an `imeta` reference, and the
  event, the audit JSONL and the git mirror hold no image bytes

### Requirement: A refused upload names the reason

Every refused upload SHALL answer with an error that names the limit it hit
(size, type, dimension, metadata that cannot be stripped, missing caption), and
a relay failure SHALL answer with the relay's reason. No upload SHALL fail
silently or be sent changed.

#### Scenario: The relay refuses

- **WHEN** the relay rejects the message
- **THEN** the route answers 502 with the relay's reason and the client is
  told the image was not sent
