---
status: actief
last_reviewed: 2026-11-25
---

# Send an image to Mark's phone

An agent can attach one picture to a ping, as a screenshot or a chart:

    IDENT=architect CHAN=architectuur ~/ratatoskr/orchestrator/ping.sh \
      --image chart.png 'p95 latency, last 7 days'

`--image <path>` has to be the **first** argument, and the caption is
required — it becomes both the notification text and the `alt` text, so there
is no silent picture without one.

## What happens to the image

`orchestrator/image_prep.py` (a `uv` script, Pillow) runs before anything is
sent:

- **Types.** PNG, JPEG or WebP, checked by magic bytes — the extension is
  never consulted. Everything else (SVG, GIF, HEIC, …) is refused.
- **Limits.** The input file must be ≤ 20 MiB and ≤ 40 megapixels. The output
  is fit inside 2560×2560 px and must come out ≤ 5 MiB.
- **No metadata survives.** The image is re-encoded from its raw pixels, so no
  EXIF, XMP, ICC profile or text chunk is carried over. The orientation is
  applied first, so a rotated photo still looks right. One image per message;
  no video, GIF, SVG or PDF.

The prepared file then goes up the same path an agent's text already takes:
`buzz messages send --content '<caption>' --file <path>`, signed with the
identity's key, to the relay's own Blossom store.

## Exit codes

| exit | meaning |
|---|---|
| 9 | `--image` was given without a caption |
| 10 | the image was refused (not PNG/JPEG/WebP, too large, or corrupt) — the reason is on stderr |

Every other `ping.sh` rule (IDENT, channel membership, the human identity
refused) applies exactly as it does for a text ping.

## The notification

Mark's phone shows `🖼 <caption>` and a tap opens the channel. The picture
itself is not in the notification — only the text.

## The thread does not show the picture (yet)

Until the follow-up change `agent-image-to-chat-read` is built, the chat
thread shows the caption only, as plain text. The image is on the relay, but
nothing in the chat fetches or renders it yet.

## Retention: 30 days

Images are kept for 30 days; a daily timer (`jobs/prune-media.sh`, systemd
`ratatoskr-media-prune.timer`) deletes older blobs from the relay's media
store. The message text itself is never deleted. See
[troubleshooting.md](troubleshooting.md) if the timer fails.
