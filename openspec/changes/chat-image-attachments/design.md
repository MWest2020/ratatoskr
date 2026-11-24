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

### Gate results (2026-11-24, host session on agent-lxc)

**1. buzz media: passes. The relay carries media natively.** Measured for the
sister change `agent-image-to-chat` (#243); see its design.md, "Measured on
2026-11-13" and "Measured on 2026-11-24":

- `buzz upload file` puts a PNG in the relay's Blossom store (`buzz-media`) and
  returns `url`, `sha256`, `size`, `type`, `dim`, `blurhash`, `thumb`; the relay
  refuses media with metadata (422); `buzz media get <sha>` returns it
  byte-identical; the media URL is 401 without Blossom auth.
- `buzz messages send --file probe.png` (as `odin`, to `#statistics`) was
  accepted. The event carries
  `["imeta","url http://192.168.178.60:3000/media/<sha>.png","m image/png","x <sha>","size 463","dim 16x16","blurhash …","thumb …/<sha>.thumb.jpg"]`
  and buzz appends `\n![image](<url>)` to `content`. The recorded event is
  `chat/testdata/imeta-event.json`. The message was deleted afterwards; the
  blob stays until a prune.

Consequence, per gate 1 above: the decision "the image does not go through the
relay" (proposal, "What changes") has to be revisited before this change is
built. The reference form is now answered by the relay itself (an `imeta` tag
on the signed event), and the content-hash store on the chat host and the
listener's fetch from the chat host may no longer be needed. Not decided here.

**2. Vision through Read: passes for every model the chat agents use.** The
chat-facet models in the handbook (`docs/agents/*.md`): `sonnet` for odin,
bouwer, marketing, ontwerper, reviewer, roodteam and pilotleider; `haiku` for
assistent; `opus` for architect. Probe: a generated 96×48 PNG with a red disc
on the left and a blue square on the right, in a scratch directory `<dir>`. Run
with the listener's reduced environment (`env -i` with `PATH`, `HOME`, `LANG`,
`TERM`, as `agent_env()`) and the absolute scope `scoped()` produces:

```
claude -p --output-format json --permission-mode dontAsk --model <m> \
  --allowedTools "Read(/<dir>/**)" \
  <<<"Read the image file <dir>/probe.png with the Read tool and describe in one sentence what shapes and colours it contains. Do not guess from the filename."
```

| `--model` | ran as | turns | denials | answer |
|---|---|---|---|---|
| `sonnet` | `claude-sonnet-5-5` | 2 | none | "The image contains a red circle on the left and a blue square on the right, side by side on a white background." |
| `haiku` | `claude-haiku-5-5` | 2 | none | "The image shows two solid shapes on a plain background: a red circle on the left and a blue square on the right." |
| `opus` | `claude-opus-5-5` | 2 | none | "The image shows a red filled circle on the left and a blue filled square on the right, both on a white background." |

Claude Code 2.1.322. The `Read` tool hands the model the image itself, not a
text rendering of the bytes, so the delivery-through-scratch-dir part of the
design holds.
