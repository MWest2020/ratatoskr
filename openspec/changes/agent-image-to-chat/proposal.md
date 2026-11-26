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
| EXIF stripping had no route in a stdlib-only chat image. | Images are stripped on agent-lxc by a stdlib-only helper that keeps the pixel data byte for byte and drops every container part not on a short keep-list. It needs no Pillow, no `uv` and no network. The relay also refuses media that carries metadata (measured). The chat image stays stdlib-only. |
| `chat/app.js` is at 200 lines. | `chat/app.js` is not touched here. The follow-up changes one existing hook line, adds no lines, and keeps the image code in a new file. |

## What changes

- **Sender: `ping.sh --image <path> 'caption'`.** This is the existing helper
  with the same IDENT and channel rules. A new stdlib-only helper
  (`orchestrator/image_prep.py` with `image_strip.py`) checks the magic bytes
  (PNG, JPEG or WebP only). It refuses files over 20 MiB and images over
  2560 px on a side. It keeps the pixel data byte for byte and drops
  everything else in the file, so no EXIF, XMP, text, comment or ICC data
  survives. It refuses what it cannot strip without changing the picture
  (a rotated EXIF orientation, an animated PNG or WebP, a CMYK, Adobe or
  RGB-coded JPEG), refuses malformed files cleanly, and refuses output over
  5 MiB. It removes accidental metadata; data hidden in the pixels on purpose
  is out of scope. Then
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

## Amended after the third architect FAIL (ratatoskr#260)

The architect's findings are folded in, and the split stays: this build is A
plus C, and the read path stays in `agent-image-to-chat-read` behind Gate 0.

- **The imeta tags must reach `notify.push` on every path.** `notify._last`
  holds `(author, content)` for a message the cooldown holds back, and `flush`
  rebuilds the push from it, so the tags would be lost and a held-back image
  would read as plain text. The tags are carried through `_last` and `flush`,
  with a seam test that calls both sides.
- **Pillow offline.** Settled at the time with a guard test. Superseded by
  the fourth FAIL amendment below: there is no Pillow any more.
- **One caption/imeta parser.** One shared fixture,
  `chat/testdata/imeta-event.json`, and `agent-image-to-chat-read` reuses a
  shared helper instead of writing a second parser.
- **Dedup versus age** is accepted and recorded in design.md.

## Amended after the fourth architect FAIL (2026-11-26)

The architect called this "the best-prepared version so far" and failed it on
the evidence for the metadata strip. Its seven gaps and six risks are settled
in design.md, "Settled by the architect's findings (2026-11-26, fourth FAIL)".
The shape does not change. It is still A plus C, with the same files, limits,
exit codes and gates.

- **No Pillow.** Pillow is not in the factory's worker image
  (`habitat-worker:1840e163`). It would arrive from PyPI on every build, CI
  run and pre-push `verify.sh`, and agent-lxc cannot resolve the old pin
  offline. The helper is now a stdlib keep-list strip, and its tests run under
  `python3 -m unittest` like every other test in the repo. The 2560 px fit
  becomes a refusal, because resizing needs a decoder.
- **Fixtures are committed now**, with their host-only generator, so the build
  never has to author a JPEG or WebP. Every test proves its input dirty
  before it calls the output clean.
- **The listener gets shorter.** The should-notify test and the reading of
  `content` and `tags` move into `notify.on_message`, so `agents/listener.py`
  goes from 200 to 199 lines. The Web Push chain is pinned on both sides.
- **The helper lives in `chat/imeta.py`** and `agents/notify.py` loads it by
  file path. **`--mention` stays** on the image branch, with a fixed fallback
  in gate 3. **The prune unit files** are installed at merge and enabled after
  gate 1.2, so the local gate stays green.
- **Dedup versus age** stays accepted.
- **After the review of #267:** bounded parsing with a truncation and
  byte-flip sweep, stricter dimension checks, `imeta` never raises, APNG and
  RGB-coded JPEG refused, exact lengths of kept parts, a restart-marker
  fixture, `SHA256SUMS`, and a refusal message that tells agents how to stay
  under 2560 px. See design.md, "Review of #267".

## Amended after the builder FAIL (2026-11-26)

The single build run (ratatoskr#243) hit 161 turns and $14.17 and stopped after
tasks 2.1 and 2.2. Decision: section 2 of tasks.md is split into three
separately buildable runs, each with its own `done_when` and tests, and a run
builds only its own tasks. Scope, files, limits and gates do not change.

- **Run A:** the stripper helper (`image_prep`, `image_strip`, `image_exif`,
  `image_testwalk`) and `ping.sh --image`. Amended after the fifth architect
  FAIL (ratatoskr#260): run A starts from main and builds to the #267 design.
  It reuses the earlier builder branch only if its SHA is pinned and the
  passing tests are named; otherwise nothing is taken over.
- **Run B:** the notify and listener image-push wiring plus `chat/imeta.py`,
  including the listener split so `agents/listener.py` stays at or under 200
  lines.
- **Run C:** `media-prune` retention, the docs, and the English-text and
  line-limit verification.

Also from the fifth architect FAIL: the comment at `agents/listener.py:159`
names `notify.on_message` instead of `notify.should_notify`, rewritten in the
same edit that lands the file at 199 lines; the source pin greps for both
`notify.should_notify(` and the stale comment name. `--content --file
--mention` together stays unproven until gate 3.1, with the fallback of
dropping `--mention` on the image branch.

## Open questions

- Docs land in run C, after A and B. Whether CI's code-without-docs check
  accepts runs A and B merging on their own is not known. If it does not, the
  sender docs (`send-an-image.md`, `ping-from-a-session.md`) move into run A.
- The follow-up change `agent-image-to-chat-read` does not exist yet. It is
  proposed separately (tasks 4.1), with the handover in this change's design.md.

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
