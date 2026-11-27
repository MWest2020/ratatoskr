# Design: images in the chat, part 1 (the server)

The split, and why, is in `proposal.md`. This file holds the decisions of
part 1 and the gate record. `chat-image-attachments-ui` and
`chat-image-attachments-deliver` have their own design.md.

## Decisions

### The image goes through the relay, signed as the session's identity

`POST /api/upload` ends in `buzz messages send --channel <cid> --content -
--file <tmp>`, run by the chat's own process, so it is signed by mark exactly
as `/api/send` is (`chat/buzzcli.buzz()` without `key`). The relay stores the
bytes in its Blossom store and puts an `imeta` tag on the event; buzz appends
`![image](<url>)` to the content (`chat/testdata/imeta-event.json`).

Why: gate 1 found the relay carries media natively, and `agent-image-to-chat`
already relies on it (its design.md, "The image goes through the relay's own
media store"). One store, one reference format (`imeta`), one parser
(`chat/imeta.py`), one retention job. The provenance is the signed event.

Rejected:
- **A content-hash store on the chat host** (the 2 Nov design). It needs the
  listener to reach the chat host, which it cannot (architect, point 1), and a
  second retention mechanism next to `media-prune`.
- **An unauthenticated GET keyed by the hash, for the listener.** The chat's
  first route readable without a session, on an app whose tailnet is the door
  (`docs/naar-een-product.md`).
- **ssh plus a sudoers helper into `ratatoskr-chat-data`.** Works, but adds
  deploy work and a second store; the image would not be part of the signed
  message.
- **Base64 in the message.** Bloats the relay, the audit JSONL and the push
  payload; the 16 KiB text path does not change.

### One image per request, and one per message

`buzz messages send --file` attaches one file, and `agent-image-to-chat` is one
image per message. The upload route takes one image and makes one message.
The 2 Nov design allowed three per message; that would mean three relay
messages or a multi-file event nobody has measured.

Rejected: multipart with up to three files (the stdlib `cgi` module is
deprecated in 3.12 and gone in 3.13, and hand-parsing multipart is more
failure surface than the feature needs).

### The body is read after the gate, with its own ceiling

`chat/server.py` `do_POST` reads at most 16 KiB and `json.loads` it before any
route. `/api/upload` branches off before that: `auth_routes.gate(h, path,
writes=True)` first (it reads headers only, so session and CSRF are checked
before a byte of body is read), then the body with a 5 MiB ceiling. Refused
before reading: a missing or non-integer Content-Length, a length over 5 MiB,
and `Transfer-Encoding: chunked` (`BaseHTTPRequestHandler` does not decode it).
The channel and the caption come in the query string (`?channel=<cid>&caption=`),
since the body is the image; the caption is required and at most 2 000
characters, as for agents.

The route's body handling lives in a new `chat/upload.py` returning
`(status, payload)`, the shape `chat/actions.py` uses, so `server.py` grows
by the branch only and stays under 200 lines.

### One stripper: `orchestrator/image_prep.py`, copied into the chat image

The stdlib keep-list strip of `agent-image-to-chat` (`image_prep.py`,
`image_strip.py`, `image_exif.py`, `image_selfcheck.py`) is the only stripper.
`chat/Dockerfile` copies these four files from `orchestrator/` into `/app/`;
`chat/upload.py` imports them from its own directory in the image and, in the
repo, loads them by file path from `../orchestrator/`, the way
`agents/notify.py` loads `chat/imeta.py`. A test pins that the Dockerfile's
copy list equals the helper's own imports, so a new helper module cannot be
forgotten in the image.

The upload route uses the helper's refusals and limits unchanged (PNG, JPEG,
WebP by magic bytes; over 2560 px, a rotated EXIF orientation, animation,
CMYK or Adobe JPEG refused; output over 5 MiB refused), and passes its
refusal text through to the client.

Rejected:
- **A second stripper in `chat/`.** Two strippers drift; #267's sweep was
  needed to get one right.
- **Pillow in the chat image.** The chat image is stdlib-only on purpose, and
  `agent-image-to-chat`'s fourth FAIL removed Pillow for the same reasons.
- **Moving the helper into `chat/`.** Touches merged code, its tests and
  `ping.sh` for no gain over a copy line in the Dockerfile.

### Errors are visible

Every refusal returns 4xx with a reason that names the limit (size, type,
dimension, metadata that cannot be stripped, missing caption); a relay
failure returns 502 with the relay's reason, cut to 200 characters. Nothing
is cut off or sent silently. AGENTS.md: "Stil falen is de fout".

### What is not here

Rendering, the read route and the composer are not in this change. Until
`chat-image-attachments-ui` is built the route has no button; it is tested
directly and from `chat/e2e/api.sh`.

## Rejected alternatives (from the 2 Nov design, still rejected)

- **A live iframe of a page in the chat.** Web view is handled, if at all, as
  a screenshot in a later `werksessies` change.
- **Giving chat agents `WebFetch`.** `werksessies` limits it to session types.
- **Letting the model fetch the file itself.** The listener validates; the
  model gets a local path only (`chat-image-attachments-deliver`).
- **Opening the habitat cage** for media access.

## Gates

1. **buzz media.** Passed (below).
2. **Vision through Read.** Passed (below).
A. **The chat's CLI sends a file.** On the chat container's CLI
   (`docker compose exec chat buzz ...` on the relay VM, `BUZZ_REF` of
   `chat/Dockerfile`), not agent-lxc's: `buzz messages send --channel <test>
   --content - --file probe.png` as mark is accepted and the event carries an
   `imeta` tag with `url`, `m`, `x`, `size`, `dim`. Record the CLI version and
   the command. If the chat's CLI lacks `--file`, a `BUZZ_REF` bump is its own
   change (`relay-deployment/spec.md`) and this one waits.

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

Decided in the split of 2026-11-27 (proposal, "Split after the architect
FAIL"): the image goes through the relay, the content-hash store and the fetch
from the chat host are dropped.

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
