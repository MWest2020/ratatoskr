# Pasting and uploading images in the chat

## Why

Mark, 2026-11-02, after asking odin whether it could see a page: *"Kun je die
zien?"* It could not. Everything the chat sends is text, so a screenshot of an
error never reaches an agent. Mark asked: *"can you do a proposal for web view
and pasting /uploading images?"*

What the code did on 2026-11-02:

- The write path is text only. `chat/server.py` caps a POST at 16 KiB,
  `chat/actions.py` sends through `buzz messages send --content -`, and the UI
  puts text in the DOM with `textContent`. `chat/` has no upload, paste handler
  or file input.
- Agents read text only. `agents/relay.py` returns message text, and
  `agents/providers.py` starts `claude -p` with the prompt on stdin under
  `--permission-mode dontAsk`.

## Split after the architect FAIL (ratatoskr#223) and the gate results

The architect failed this change on 2026-11-02 (run
`20261102-082217-10331`, ratatoskr#223) on four points a builder would have to
guess, and called it too large for one build:

1. **Transport.** "The listener fetches the file from the chat host", but the
   listener runs on agent-lxc and the chat sits on the relay VM at
   `127.0.0.1:8090` behind `tailscale serve`, every `/api/` route behind a
   session the listener does not have.
2. **EXIF.** No way to strip it in a stdlib-only chat image.
3. **Read-back.** Showing the image after a reload or on a second device needs
   a GET route that is in no task or spec.
4. **Render hook.** `chat/app.js` is at the 200-line limit and the hook for
   turning a reference into an `<img>` is unnamed.

Since then, the sister change `agent-image-to-chat` (agent → Mark) was built
and merged (#270, #271, #273, 26 Nov 2026), and both gates of this change were
recorded (#259). Gate 1 found that the relay carries media natively: an image
uploaded with `buzz messages send --file` lands in the relay's Blossom store,
signed by the sender, with an `imeta` tag on the event. That answers points 1
and 2, and `agent-image-to-chat-read` owns points 3 and 4:

| Architect's point | Answer |
|---|---|
| 1. transport | Through the relay, as agents already send. The chat uploads with `buzz messages send --file`, signed as the session's identity (mark). The listener reads the blob from the relay it already talks to (`192.168.178.60:3000`) with `buzz media get`. No new route on the chat, no new network path, no new secret. |
| 2. EXIF | The stdlib keep-list strip that #270 built (`orchestrator/image_prep.py`, `image_strip.py`, `image_exif.py`, `image_selfcheck.py`), one source, copied into the chat image by the Dockerfile. The relay also refuses media that carries metadata (measured, 422). |
| 3. read-back | `GET /api/media/<sha256>` behind the session gate, already designed in `agent-image-to-chat`'s "Handed to `agent-image-to-chat-read`". It serves any image message, Mark's included. |
| 4. render hook | Owned by `agent-image-to-chat-read` (one existing hook line, image code in `chat/app-image.js`). This work adds no rendering of its own. |
| retention | The relay's media store and the `media-prune` job of `agent-image-to-chat`, not a second store on the chat host. See the open questions. |

So the change is cut in three, each buildable and reviewable alone:

- **`chat-image-attachments` (this change): the server.** `POST /api/upload`
  checks and strips one image and sends it through the relay as a message from
  the session's identity, with the caption as text.
- **`chat-image-attachments-ui`: the composer.** Paste and an attach button,
  one image per message, visible refusals. Depends on this change and on
  `agent-image-to-chat-read`, so the image Mark sends is shown in the thread.
- **`chat-image-attachments-deliver`: the listener.** An image in a human
  member's message reaches the agent as a file in a per-turn scratch
  directory. Depends on `agent-image-to-chat` (merged: `chat/imeta.py` and the
  recorded event). It does not need the server or the UI to be built first,
  since its tests run on the recorded event.

## What changes

- **`POST /api/upload`.** Behind the same session gate and session token as
  `/api/send`. One image per request, which is one message. The body is read
  with its own 5 MiB ceiling after the gate, never through the 16 KiB JSON
  path; a missing Content-Length or a chunked body is refused. The type is
  decided by magic bytes. The image is prepared by the same stdlib helper as
  `ping.sh --image`, with the same refusals. Then the chat runs
  `buzz messages send --file` with the caption, so the message is signed by
  mark like any message from the chat.
- **The image goes through the relay.** This reverses the earlier "the image
  does not go through the relay" decision, as gate 1 asked. The relay event
  carries an `imeta` reference; the bytes live in the relay's Blossom store,
  not in the event, the audit JSONL or the git mirror.
- **Visible errors.** Every refusal names the limit it hit.
- **The chat image** copies the four helper files from `orchestrator/`, and
  its pin moves one minor version.

## Gates

Both original gates passed (design.md, "Gate results"). One new gate, before
the build:

- **Gate A (host).** On the chat container's own CLI (`BUZZ_REF` in
  `chat/Dockerfile`), `buzz messages send --file` with `--content -` as mark is
  accepted and the event carries the `imeta` tag of
  `chat/testdata/imeta-event.json`. Recorded in design.md with the exact
  command. `agent-image-to-chat` measured this on agent-lxc's CLI, not on the
  chat's.

## Out of scope

- The composer (`chat-image-attachments-ui`) and the listener delivery
  (`chat-image-attachments-deliver`).
- Showing images in the thread, and the read route:
  `agent-image-to-chat-read`.
- More than one image per message; GIF, SVG, PDF, video.
- Resizing or rotating an image. What the helper cannot strip without
  changing pixels (over 2560 px, a rotated EXIF orientation) is refused with
  its reason, as for agents.
- The research-session screenshot (a later `werksessies` change), a live
  iframe (rejected), web access for chat agents, anything in the habitat cage.

## Scheduling

Mark, 2026-11-02: *"Implement the proposal after all the other work... there's
quite a bit open."* That stands. None of the three parts is built before
`agent-image-to-chat` is archived; the UI part also waits for
`agent-image-to-chat-read`.

## Open questions

- **The promises change.** This split replaces "the image bytes do not travel
  through the relay", "3 images per message" and "a content-hash store on the
  chat host" with: through the relay, one image per message, the relay's
  store. Mark merges it. Default: the amendment PR stays open and nothing is
  built until he does.
- **Retention of Mark's own images.** `media-prune` deletes by extension today,
  and ratatoskr#272 asks whether it may delete images that are not agent media.
  Under #272's default (a hash list from agent-authored messages only), the
  images Mark sends would never be pruned. Default: the hash list covers every
  member's image messages older than 30 days, so Mark's images live 30 days
  like an agent's; the 27 Aug images of unknown origin stay out, as #272's
  default says.

## Depends on

`agent-image-to-chat` (the stdlib image helper, the relay media path and
`media-prune`).
