# Design: images in the chat

## Decisions

### The message carries a reference, not the image

The message holds a reference to a content hash. The listener fetches the file
from the chat host. The audit JSONL, the git mirror and push payloads stay
small, and the existing text path does not change.

The form of the reference (a `[img sha256:…]` line in the text, or a tag if the
buzz CLI allows it) follows from gate 1 and is an open question in the
proposal.

### Upload is its own route with its own ceiling

`POST /api/upload` sits behind the same session gate and session token as
`/api/send`. It is not squeezed into the 16 KiB limit of `/api/send`. Ceilings:
5 MiB per image, 3 images per message.

### The server decides what a file is

Only PNG, JPEG and WebP. The type comes from magic bytes, not from the
Content-Type the browser sends. SVG is refused because it is executable
content. EXIF is stripped. The file is stored under its content hash.

### The listener validates again and delivers through a scratch directory

The listener, not the model, fetches the file and checks it a second time. It
writes the file to a per-turn scratch directory and puts the path in the
prompt. The agent reads it with `Read(<dir>/**)`, the same pattern `scoped()`
in `agents/providers.py` already applies. No new tool is added. The directory
is removed after the turn.

### Errors are visible

Over the limit, wrong type, failed fetch: each produces a message that says
what happened. This follows AGENTS.md, "Stil falen is de fout".

### Tests

The failure mode here is a seam: the upload route and the listener each pass
their own tests while the hand-over between them breaks. So there is a test
that calls both sides, plus an e2e in `chat/e2e`.

## Rejected alternatives

- **Base64 in the Nostr event.** Bloats the relay, the audit JSONL and the push
  payload, and breaks the existing text path.
- **A live iframe of a page in the chat.** Rejected; web view is handled, if at
  all, as a screenshot in a later `werksessies` change.
- **Giving chat agents `WebFetch`.** `werksessies` limits it to session types,
  because what is on the web is written by strangers.
- **Letting the model fetch the file itself.** The listener validates; the
  model gets a local path only.
- **Opening the habitat cage** for media access. Needs an approved amendment on
  habitat's `worker-execution` spec and is not part of this.

## Gates

1. **buzz media.** Check whether the buzz CLI or relay accepts media. The
   outcome decides the reference form. If it can carry media natively, revisit
   the "image does not go through the relay" decision before building.
2. **Vision through Read.** Check that `claude -p` under `dontAsk` gives the
   model the actual image through `Read`, and that the model in `agents.yml`
   for the agent supports vision. If not, amend this design first.
