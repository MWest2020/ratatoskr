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

## The other direction stays parked

#223 (`chat-image-attachments`) is the reverse: Mark pastes an image, agents
read it. Its architect FAILED on 2026-11-02, and it stays parked. This change
does not touch it. The table shows how this change avoids each trap the
architect named:

| #223 trap | Here |
|---|---|
| The listener has to fetch the file from the chat host, and the listener does not run there. | Nothing fetches from the listener, and the listener fetches nothing. The bytes go up the path agents already use (`ping.sh` → buzz → relay, signed with the identity's key). They come down the path the chat already uses (chat → relay over the internal `buzz-net`). |
| An unauthenticated read route would be the cheapest transport. | The only new route, `GET /api/media/<sha256>`, sits behind the existing session gate. The relay's own media URL answers 401 without Blossom auth (measured, see design). |
| Whether agent-lxc reaches the chat on the tailnet (:8090) was never recorded. | No new network path. agent-lxc → relay at `192.168.178.60:3000` (what `ping.sh` already uses), chat → relay over `buzz-net`, phone → chat over `tailscale serve`. |
| Retention was unanswered. | Images are kept 30 days. A daily job deletes older ones, and the job fails loudly when the bucket stays over 2 GiB. |
| EXIF stripping had no route in a stdlib-only chat image. | Images are stripped on agent-lxc, where `uv` scripts with dependencies are normal (`push-notify.py`). The relay also refuses media that carries metadata (measured). The chat image stays stdlib-only. |
| `chat/app.js` is at 200 lines. | One existing hook line is changed and no lines are added. The image code lives in a new file. |

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
- **Chat server.** `/api/messages` gains an `images` field for each message,
  read from the `imeta` tags of the event. The new `GET /api/media/<sha256>`,
  behind the session gate, fetches the blob with `buzz media get` under the
  chat's own key. It serves the blob only when its magic bytes say PNG, JPEG or
  WebP, with a fixed Content-Type, `nosniff` and `no-store`. A missing blob
  returns 410 "expired", and any other failure returns 502 with the reason.
- **Chat UI.** A new `chat/app-image.js` shows the image inline under the
  caption. Tapping it opens a full-screen view, and tapping again or Back
  closes it. A failure is shown as text that names the reason: expired, offline
  or relay error.
- **Notification.** For an image message the push reads `🖼 <caption>`, and a
  tap opens the channel. The image itself is not in the notification (see the
  gates).
- **Retention.** A daily timer on agent-lxc runs a pinned rclone one-shot
  (`media-prune`, a compose profile on the relay VM). It deletes image blobs
  older than 30 days, then fails if the bucket is still over 2 GiB.
- **Docs** for the sender, the limits, the retention and the failures.

## Gates

Three were measured on 2026-11-13 and are recorded in design.md. An agent key
can upload. The relay refuses metadata. Read-back with `media get` is
byte-identical. Three remain:

1. The `imeta` tag that `buzz messages send --file` actually writes. Sending a
   probe message from this proposal session was refused by the auto-mode
   classifier, so this gate is still open.
2. The bucket key layout and what else lives in `buzz-media`, before the prune
   is enabled.
3. On Mark's phone: the image renders in the installed PWA and opens full size.
   Rich notifications with the picture in them are **not** in this change. This
   gate records whether Chrome on Android could show one, for a later decision.

## Out of scope

- #223, Mark → agents. Agents do not get images in their prompts.
- Chat-native agents (odin and the listener turns) attaching images from a turn.
  The listener's answer path stays text. See the open questions.
- The image inside the push notification.
- More than one image per message, and video, GIF, SVG or PDF.
- An image as a thread reply (`--reply-to`).

## Open questions for Mark

1. Keep images for 30 days? Default: yes. The message text stays forever; only
   the picture expires and shows "image expired".
2. Text-only notification (`🖼 caption`, tap opens the thread), or work on a
   picture inside the notification later? Default: text-only now. The gate
   outcome is recorded, and a separate change follows only if you ask.
3. Should chat-native agents (odin and the other listener agents) also be able
   to attach an image from a chat turn? Default: no, not in this change. It
   needs a marker in the answer path and a tool grant, so it gets its own
   proposal.
