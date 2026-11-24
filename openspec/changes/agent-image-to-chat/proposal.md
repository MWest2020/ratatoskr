# Agents send an image to Mark's phone

## Why

Mark, 2026-11-13, on agents sending him an image (a screenshot, a chart) that
he sees in the Ratatoskr chat on his phone: *"klinkt heel erg cool, mag
opgepakt worden"*.

Today every agent post is text. A session reports with
`IDENT=<x> CHAN=<y> orchestrator/ping.sh 'text'`, which signs with the
identity's key and runs `buzz messages send` against the relay. The chat reads
the same relay with `buzz messages get` and renders text through
`textContent`. The listener sends a text push for new messages
(`agents/notify.py`). A chart or a screenshot of a failing page cannot reach
Mark except as a description.

## Split after the second architect FAIL (ratatoskr#260)

The second architect FAIL on this change (ratatoskr#260) had four findings. The
decision is to cut the change in two:

- **This change, `agent-image-to-chat`,** covers objective A (the sender: `ping.sh
  --image`, `image_prep.py`) and objective C (the notification and the
  retention).
- **Follow-up `agent-image-to-chat-read`** covers objective B: the
  `GET /api/media/<sha256>` read path, `chat/media.py`, the `images` field of
  `/api/messages`, the inline image and full-screen view in the chat, and the
  `webchat-pwa` requirement for the response headers. It is **built only after
  Gate 0 is recorded in its design.md**. Everything about it that was in this
  change (the route, its status codes, the UI, the 0.19.0 / `v33` triple, the
  seam test, `chat/e2e/image.js`) leaves this change and is handed over in
  design.md, "Handed to `agent-image-to-chat-read`".

Until the follow-up is built, an agent can send an image and Mark gets the
`🖼 caption` push, but the thread does not show the picture. This change does
not make it visible.

## The other direction stays parked

#223 (`chat-image-attachments`) is the reverse: Mark pastes an image, agents
read it. Its architect FAILED on 2026-11-02, and it stays parked. This change
does not touch it. The table shows how this change avoids each trap the
architect named:

| #223 trap | Here |
|---|---|
| The listener has to fetch the file from the chat host, and the listener does not run there. | Nothing fetches from the listener, and the listener fetches nothing. The bytes go up the path agents already use (`ping.sh` → buzz → relay, signed with the identity's key). They come down the path the chat already uses (chat → relay over the internal `buzz-net`). |
| An unauthenticated read route would be the cheapest transport. | This change adds no route. The only new route, `GET /api/media/<sha256>`, belongs to the follow-up `agent-image-to-chat-read` and sits behind the existing session gate. The relay's own media URL answers 401 without Blossom auth (measured, see design). |
| Whether agent-lxc reaches the chat on the tailnet (:8090) was never recorded. | No new network path. agent-lxc → relay at `192.168.178.60:3000` (what `ping.sh` already uses), chat → relay over `buzz-net`, phone → chat over `tailscale serve`. |
| Retention was unanswered. | Images are kept 30 days. A daily job deletes older ones, and the job fails loudly when the bucket stays over 2 GiB. |
| EXIF stripping had no route in a stdlib-only chat image. | Images are stripped on agent-lxc, where `uv` scripts with dependencies are normal (`push-notify.py`). The relay also refuses media that carries metadata (measured). The chat image stays stdlib-only. |
| `chat/app.js` is at 200 lines. | `chat/app.js` is not touched here. The follow-up changes one existing hook line, adds no lines, and keeps the image code in a new file. |

## What changes

- **Sender: `ping.sh --image <path> 'caption'`.** This is the existing helper
  with the same IDENT and channel rules. A new uv script
  (`orchestrator/image_prep.py`) checks the magic bytes (PNG, JPEG or WebP
  only). It refuses files over 20 MiB and images over 40 megapixels. It
  re-encodes from raw pixels, so no EXIF, XMP, text or ICC data survives. It
  fits the image inside 2560×2560 px and refuses output over 5 MiB. Then
  `buzz messages send --file` uploads the image to the relay's Blossom store
  and attaches it to the signed message. One image per message, and the caption
  is required.
- **Notification.** For an image message the push reads `🖼 <caption>`, and a
  tap opens the channel. The image itself is not in the notification (see the
  gates).
- **Retention.** A daily timer on agent-lxc runs a pinned rclone one-shot
  (`media-prune`, a compose profile on the relay VM). It deletes image blobs
  older than 30 days, then fails if the bucket is still over 2 GiB.
- **Docs** for the sender, the limits, the retention and the failures.

## Gates

**Gate 0 is no longer a gate of this change.** It measures `buzz media get` and
a cross-identity blob read on the chat container's CLI (`BUZZ_REF=4baccd53`),
which only the read path needs. It moves to `agent-image-to-chat-read`, which is
built only after Gate 0 is recorded in its design.md. The exact `buzz media get`
invocation, including the stdout flag, is part of what Gate 0 records; `-o -` is
unverified and is not assumed. A `BUZZ_REF` bump would force a relay image bump
(`relay-deployment/spec.md:38`) and goes in its own change.

Three were measured on 2026-11-13 and are recorded in design.md. An agent key
can upload. The relay refuses metadata. Read-back with `media get` is
byte-identical. Those, too, were measured on agent-lxc's CLI. Gate 1 (the
`imeta` shape) was recorded on 2026-11-24, see design.md, and is the only one
the build waits on. Three remain for this change:

1. The bucket key layout and what else lives in `buzz-media`, before the prune
   is enabled.
2. A real `ping.sh --image` with a prepared PNG, JPEG and WebP, accepted by the
   relay.
3. On Mark's phone: the `🖼 caption` notification and its tap. Rich
   notifications with the picture in them are **not** in this change. This gate
   records whether Chrome on Android could show one, for a later decision.

## Out of scope

- The read path and everything the chat shows: `agent-image-to-chat-read`.
- #223, Mark → agents. Agents do not get images in their prompts.
- Chat-native agents (odin and the listener turns) attaching images from a turn.
  The listener's answer path stays text. See the decisions.
- The image inside the push notification.
- More than one image per message, and video, GIF, SVG or PDF.
- An image as a thread reply (`--reply-to`).

## Open questions

- The decision names three things as objective B (the route, `chat/media.py`,
  the headers requirement). The `images` field, the inline image and the
  full-screen view cannot work without the route, so they are placed in the
  follow-up too. If they should stay here, say so.
- Whether Pillow can be resolved by `uv` in the build cage is unknown. The
  Pillow test fails rather than skips when it cannot (design.md, "Tests"). If
  the cage cannot resolve it, the choice is to vendor the wheels or to accept
  that the metadata-strip test only runs on the host. Not decided.
- The follow-up change `agent-image-to-chat-read` does not exist yet. It is
  proposed separately, with the handover in this change's design.md.

## Decisions (Mark, 2026-11-14 by mail: "defaults ok")

1. Keep images for 30 days? Decided: yes. The message text stays forever; only
   the picture expires and shows "image expired".
2. Text-only notification (`🖼 caption`, tap opens the thread), or work on a
   picture inside the notification later? Decided: text-only now. The gate
   outcome is recorded, and a separate change follows only if you ask.
3. Should chat-native agents (odin and the other listener agents) also be able
   to attach an image from a chat turn? Decided: no, not in this change. It
   needs a marker in the answer path and a tool grant, so it gets its own
   proposal.
