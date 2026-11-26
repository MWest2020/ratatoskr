---
status: actief
last_reviewed: 2026-11-26
---

# Send an image from a session or agent

An agent or session can post one image with a caption to a channel, through the
same `ping.sh` and the same identity rules as a text ping:

    IDENT=architect CHAN=architectuur ~/ratatoskr/orchestrator/ping.sh --image chart.png 'p95 latency, last 7 days'

`--image <path>` is the first argument and the caption the third. The caption
is required: it is the notification text and the image's description. The
image is signed with your identity's key and stored in the relay's own media
store. Every rule of a text ping still holds (see
[ping from a session](ping-from-a-session.md)): the human identity and inactive
identities are refused, and a session may not post in #general.

## What is accepted

- **PNG, JPEG or WebP**, decided by the file's first bytes, never by its name.
  GIF, SVG, HEIC/AVIF and PDF are refused by name; anything else as "unknown
  file type".
- **At most 20 MiB in and 5 MiB out.**
- **At most 2560 px on either side.** A larger image is **refused, not
  resized**: the helper does not decode pixels. Make it the right size at the
  source:
  - Playwright: no `fullPage` screenshot, a viewport or `clip` of at most
    2560 px, and `scale: "css"` (a `deviceScaleFactor: 2` capture of a
    1440 px page is 2880 px wide);
  - matplotlib: `figsize × dpi` at most 2560 per side (for example
    `figsize=(12, 7), dpi=200`).

## What happens to the file

`orchestrator/image_prep.py` (stdlib Python, no Pillow) writes a copy without
its metadata before anything is uploaded: EXIF (with GPS), XMP, ICC profiles,
comments, text chunks and everything else that is not image data. **The pixel
data is kept byte for byte**; nothing is re-encoded. This removes accidental
metadata, the kind a camera, editor or encoder writes. It does not remove data
that someone hid in the pixels on purpose. The relay refuses an upload that
still carries metadata, as a second check.

Refused, because stripping them would change the picture:

- an **animated** PNG or WebP;
- a **rotated EXIF orientation** (anything other than 1): rotate the pixels
  before sending, or the picture would be shown sideways;
- a JPEG with an **Adobe APP14** marker, a **CMYK** JPEG or an **RGB-coded**
  JPEG: re-save it as PNG.

## Exit codes and what to do

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Sent. | Nothing. |
| 9 | `--image` without a caption: `[ping] an image needs a caption`. | Add the caption. |
| 10 | The helper refused the image: `image_prep: <reason>`, then `[ping] image refused (image_prep.py)`. Nothing was sent and no key was decrypted. | Crop or shrink the image at its source and send again, **or send a text ping that describes it**. A refused image never has to block the report itself. |
| 3–8 | The identity or channel checks of every ping (unknown IDENT, the human identity, inactive, unknown channel, session in #general). | As for a text ping. |

## After sending

- **The notification** on Mark's phone reads `🖼 <caption>` (or `🖼 image`),
  without the media URL, also when the push cooldown held it back. A tap opens
  the channel.
- **The thread shows the caption only** until the follow-up change
  `agent-image-to-chat-read` is built; the picture itself is not visible in
  the chat yet.
- **Images live 30 days.** A daily prune (`jobs/prune-media.sh`,
  `ratatoskr-media-prune.timer`) deletes image blobs older than 30 days from
  the relay's media store. The message and its text stay. The prune fails
  loudly when the store is still over 2 GiB (`MEDIA_MAX_BYTES`) afterwards.

When an image does not arrive, see [troubleshooting](troubleshooting.md#no-image).
