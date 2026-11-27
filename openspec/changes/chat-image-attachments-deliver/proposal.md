# An image in Mark's message reaches the agent

## Why

Part 3 of the split of `chat-image-attachments` (its proposal, "Split after
the architect FAIL (ratatoskr#223) and the gate results"). Mark's question of
2026-11-02, *"Kun je die zien?"*, is answered here: when Mark's message carries
an image, the agent that answers gets it as a file it can read.

Gate 2 of `chat-image-attachments` showed that `claude -p` under `dontAsk`
hands the model the image itself through `Read`, for sonnet, haiku and opus.
Gate 1 showed the image lives in the relay's media store, referenced by an
`imeta` tag on the signed event (`chat/testdata/imeta-event.json`). So the
listener needs no route on the chat and no new network path: it already talks
to the relay at `192.168.178.60:3000` with each agent's key.

## What changes

- **`agents/attachments.py`** (new): for the message that triggers a turn,
  read its images with `chat/imeta.py` (`from_tags`, loaded by file path as
  `agents/notify.py` does), **only when the message is Mark's own** (checked by
  pubkey, as `!build` is). For each image (one per message today): `buzz media
  get <sha256>` with the answering agent's key, a 5 MiB read ceiling, magic
  bytes again (PNG, JPEG, WebP only), and the sha256 of the bytes equal to the
  tag's `x`. Write it to a per-turn scratch directory under the listener's
  working directory.
- **The prompt names the path.** The agent reads it with the `Read` grant it
  already has (`Read(./**)` from `providers.scoped`, relative to the
  listener's working directory). No new tool.
- **Cleanup on every exit** of the turn: the scratch directory is removed in a
  `finally`, including a timeout, an exception and a consult.
- **A failed delivery is said,** in the channel, with which image and why
  (expired, relay error, wrong type, hash mismatch, too large), and the turn
  does not run as if there were no image.
- **Tests on the seam,** driven by the recorded event, and docs.

## Gates

- **Gate D (host).** On agent-lxc's CLI, as an agent identity (not mark),
  `buzz media get` of a blob uploaded by mark returns it byte-identical, and an
  unknown hash gives 404. Record the exact invocation, including how the bytes
  reach a file or stdout (`-o -` is unverified and not assumed). If an agent
  key cannot read mark's blob, this design changes before anything is built.

## Out of scope

- The upload route and the composer (`chat-image-attachments`,
  `chat-image-attachments-ui`). This change can be built before them: its
  tests use the recorded event, and Mark can already send an image from any
  client that attaches through the relay.
- Images in an agent's own message, or in a session's or another agent's
  message: never fetched (an agent could otherwise make the listener fetch by
  hash).
- Images in older messages of the context window: only the triggering
  message's image is delivered.
- Chat agents attaching images to their answers (`agent-image-to-chat`,
  decision 3: its own proposal).

## Depends on

`agent-image-to-chat` (`chat/imeta.py`, the recorded event, the relay media
path)

## Open questions

- A shared room (`room(...)`) can start several turns on one message. Default:
  each turn fetches into its own scratch directory; the fetch is cheap and the
  turns stay independent.
