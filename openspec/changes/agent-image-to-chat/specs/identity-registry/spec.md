## ADDED Requirements

### Requirement: The ping helper can attach one prepared image

The ping helper SHALL accept `--image <path>` followed by a caption. It SHALL
post the image and the caption as one message, signed with the key of the
calling `IDENT`. Every existing refusal of the helper (unknown identity, the
human identity, an inactive identity, a session in the hub channel) SHALL
apply unchanged. Before upload the helper SHALL accept only PNG, JPEG and WebP
as decided by magic bytes. It SHALL remove every EXIF, XMP, ICC, comment and
text block while leaving the image data unchanged. It SHALL refuse an image
over 2560 pixels on either side, an image whose EXIF orientation is not the
default, and a result over 5 MiB. A refusal SHALL name the reason and SHALL
post nothing. A caption SHALL be required.

#### Scenario: A session sends a chart

- **WHEN** a session runs the helper with its own `IDENT`, a project channel,
  `--image chart.png` and a caption
- **THEN** one message appears in that channel, signed by that session's key,
  with the caption and the image attached

#### Scenario: Metadata does not leave the host

- **WHEN** the input is a JPEG with GPS coordinates in its EXIF and the
  default orientation
- **THEN** the uploaded bytes contain no EXIF segment, and the image data is
  byte-identical to the input's

#### Scenario: A rotated photo is refused, not shown sideways

- **WHEN** the input's EXIF orientation is anything other than the default
- **THEN** the helper refuses it, names the orientation, and posts nothing

#### Scenario: Wrong type behind a right name

- **WHEN** the file is called `shot.png` but holds SVG text
- **THEN** the helper refuses it, names the type problem, and posts nothing

#### Scenario: Too large after preparation

- **WHEN** the prepared image is still over 5 MiB
- **THEN** the helper refuses it, states the size and the limit, and posts
  nothing

#### Scenario: The human identity stays refused

- **WHEN** the helper is called with `--image` and the `IDENT` of the human
  identity
- **THEN** it refuses as it does without `--image`, and nothing is uploaded
