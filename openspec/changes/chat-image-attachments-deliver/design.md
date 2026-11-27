# Design: the listener half

## Decisions

### The listener reads from the relay, not from the chat host

The image is in the relay's Blossom store (gate 1 of
`chat-image-attachments`). The listener already reaches the relay over the
LAN with every agent's key, so it fetches with `buzz media get <sha256>` under
the answering agent's key (Blossom get auth). This answers the architect's
first point on #223: the chat host is not involved at all.

Rejected:
- **Fetch from the chat host** (the 2 Nov design). The listener runs on
  agent-lxc; the chat is on the relay VM behind `tailscale serve` and a
  session gate.
- **The relay's media URL over plain HTTP.** 401 without Blossom auth
  (measured 2026-11-13); signing it by hand duplicates what the CLI does.
- **A fixed fetch identity** (for example `odin` for every turn). The turn's
  own agent fetching keeps the access in the same audit line as the turn.

### Only Mark's own messages are read for images

`attachments.py` reads images only from the triggering message, and only when
its pubkey is Mark's (the same check `!build` uses, never a name in the text).
An agent, a session or a revoked key never makes the listener fetch. The
architect named the risk: a reference in agent output would let an agent make
the listener fetch by hash.

Rejected: any human member (there is one human member today; a second one
is a decision for then, not a branch for nobody).

### Validate again, and bind to the tag

The listener checks what it got, not what the tag says: a 5 MiB ceiling while
reading, magic bytes for PNG, JPEG or WebP, and sha256 of the bytes equal to
the tag's `x`. The tag's `m` is not trusted for the file name; the extension
comes from the magic bytes.

### Scratch under the working directory, removed in `finally`

`providers.run` calls `scoped(allow)` with neither `root` nor `extra`, so the
`Read` grant is `Read(./**)` relative to `/home/agent/ratatoskr-listener`. The
scratch directory is `./.turn-media/<turn-id>/` under that working directory,
so the existing grant covers it, with no new tool and no signature change.
`.turn-media/` is gitignored. `run_turn` creates it before the prompt and
removes it in a `finally` that covers a timeout, an exception and the consult
path (`agent_turn.run_turn`'s recursion for a consulted agent gets its own
directory and its own `finally`). A sweep at listener start removes leftovers
from a crash.

Rejected: a directory under `/tmp` with `scoped(..., extra=...)` threaded
through `providers.run` (a signature change in the one place that decides
what a turn may read, for no gain).

### A failed delivery stops the turn and says why

If any image of the message cannot be delivered, the listener posts in the
channel which image failed and why (`image expired (kept 30 days)` on a relay
404, the relay's reason on another failure, `not a PNG, JPEG or WebP`,
`hash does not match`, `over 5 MiB`), and does not run the turn. An answer
written without the image Mark asked about would be confidently wrong.

Rejected: run the turn with a note in the prompt (the model may still answer
as if it saw the picture).

### The prompt

One line after the message text: `Attached image: <relative path> (PNG,
1080x2400). Read it with the Read tool before answering.` No base64, no
description of the image by the listener.

## Rejected alternatives

- **Letting the model fetch the file itself.** The listener validates; the
  model gets a local path only.
- **Giving chat agents `WebFetch`.** `werksessies` limits it to session types.
