# Design: agent → relay → push, one image per message

Scope after the split (ratatoskr#260): this change is the **sender** (A) and the
**notification and retention** (C). The read path (B) is the follow-up
`agent-image-to-chat-read`; what it inherits is in "Handed to
`agent-image-to-chat-read`" below.

## The path

```
agent-lxc                              relay VM (buzz-relay)
─────────                              ─────────────────────
IDENT=x CHAN=y ping.sh --image p 'c'
  ├─ image_prep.py  (python3, stdlib only)
  │    magic bytes → allowlist strip (pixel data untouched) → ≤2560 px, ≤5 MiB
  └─ buzz messages send --file  ──LAN──▶ relay :3000
                                          ├─ Blossom store (SeaweedFS, buzz-media)
                                          └─ signed event + imeta tag
listener (agent-lxc) sees the event ─▶ notify.py "🖼 caption" ─▶ push-notify.py ─▶ FCM ─▶ notification
```

Every hop in this picture already exists and already carries traffic today.
Only `--file`, the `🖼` prefix and the prune are new. Showing the image in the
chat (`chat → relay over buzz-net`, `GET /api/media/<sha256>`, the PWA) is the
follow-up.

## Measured on 2026-11-13 (gate evidence)

Run from agent-lxc as identity `bouwer`, with the key from SOPS (as `ping.sh`
does), against `ws://192.168.178.60:3000`:

| Probe | Result |
|---|---|
| `buzz messages send --help` | `--file <FILES>  Attach file(s) — uploads and includes as imeta tags` |
| `buzz media get --help` | `Download relay media with Blossom get auth`; input is a `sha256[.ext]` |
| `buzz upload file` on a 4×4 PNG **with a `tEXt` chunk** | `relay error 422: media contains metadata or a non-canonical metadata channel` (rc 2) |
| `buzz upload file` on the same PNG without `tEXt` | rc 0; JSON has `url` (`http://192.168.178.60:3000/media/<sha>.png`), `sha256`, `size`, `type: image/png`, `dim: 4x4`, `blurhash`, `thumb` (`<sha>.thumb.jpg`) |
| `buzz media get <sha>` and `<sha>.png` | rc 0, output byte-identical (sha256 matches) |
| `buzz media get <64 zeros>` | `relay error 404: {"error":"not found"}`, rc 2 |
| `curl` of the media URL and the thumb URL, no auth | `401` for both |
| `buzz upload file` with SVG text in a `.png` file | refused client-side: `unsupported file type: application/octet-stream`, rc 1 |
| `buzz upload file` on a 5,224,228-byte PNG | rc 0, 2.3 s |

Two blobs from these probes sit in `buzz-media`: the 4×4 PNG `2439351e…` and
the 5 MiB random PNG `db8b9613…`. The first prune run deletes both.

These were measured on agent-lxc's CLI, not on the chat container's. What was
**not** measured is how `media get` writes to stdout: none of the probes used
`-o -`. See the handover below.

## Measured on 2026-11-24 (gate 1, imeta shape)

Run from agent-lxc by the coding session as identity `odin` (a member of
`#statistics`, pubkey `b0e20b30…`), key from SOPS as `ping.sh` does, against
`ws://192.168.178.60:3000`. The image was a generated 16×16 RGB PNG with only
`IHDR/IDAT/IEND` (463 bytes, sha256 `bc9854f9…871e`).

| Step | Result |
|---|---|
| `buzz messages send --channel <#statistics> --content '<caption>' --file probe.png` | rc 0, `{"accepted":true,"event_id":"4464f065…"}` |
| `buzz messages get --channel <#statistics> --since <t0-60>` | the event, kind 9, committed verbatim as `chat/testdata/imeta-event.json` |
| `buzz messages delete --event 4464f065…` | rc 0, `accepted` (tombstone `6759d873…`) |
| `messages get --since <t0-60>` again | 0 events: the message is gone |
| `buzz media get bc9854f9…` after the delete | rc 0, byte-identical: **deleting the message does not delete the blob** |

The `imeta` tag, in this order:

```
["imeta",
 "url http://192.168.178.60:3000/media/<sha256>.png",
 "m image/png",
 "x <sha256>",
 "size 463",
 "dim 16x16",
 "blurhash <string>",
 "thumb http://192.168.178.60:3000/media/<sha256>.thumb.jpg"]
```

Both `x` and `url` are present, and `x` equals the sha256 of the uploaded
bytes. The only other tag is `["h", "<channel uuid>"]`.

**`content` gains the URL.** buzz appends a Markdown image line to the text:

```
<caption>\n![image](http://192.168.178.60:3000/media/<sha256>.png)
```

So the caption shown in a notification is `content` with the whole
`![image](…/media/<hash>.<ext>)` line (with its leading newline) removed, not
just the URL; removing only the URL would leave `![image]()`. The notify test
uses this recorded content.

The probe blob `bc9854f9…` now sits in `buzz-media` next to the two from
2026-11-13; the first prune deletes it. Because a message delete leaves the
blob in place, the prune is the only thing that ever removes an image.

## Decisions

### The image goes through the relay's own media store

`buzz messages send --file` uploads to the relay's Blossom store and puts the
reference into the signed event. The bytes therefore travel with the identity's
signature and the relay's closed membership, which is the authentication agents
already use. Mark asked for exactly that: the same authenticated path, with no
new door.

Rejected:
- **ssh plus a sudoers helper into `ratatoskr-chat-data`** (the
  `publish-board.sh` pattern). It works, but the image would not be part of the
  signed message, the provenance would live in two places, and it would add a
  second store next to the one the relay already runs.
- **Base64 in the message text.** It bloats the relay, the audit trail and the
  push payload, and the 16 KiB text path does not change for this.
- **A new HTTP upload route on the chat for agents.** That is #223's trap. It
  needs a credential for agent-lxc on a session-gated app, plus tailnet
  reachability of :8090 that nobody has recorded.

### The change is split: sender and notification now, read path later

The second architect FAIL (ratatoskr#260) found that the read path was the part
the build could not prove from inside the cage: it rests on a CLI invocation
nobody measured on the chat's own binary, and on a response-headers design
that the chat server cannot yet emit (see the handover). Keeping it in this
change would block the sender and the retention on it.

Rejected:
- **Keep one change and gate the whole build on Gate 0.** The sender and the
  retention do not depend on the chat's CLI; a negative Gate 0 (a `BUZZ_REF`
  bump, its own change) would hold them for nothing.
- **Build the read path with its open points and fix it in review.** The
  architect failed it twice on exactly these points.

Until the follow-up is built the thread shows the caption only. That is
accepted, and it is stated in the proposal.

### Preparing the image: a stdlib allowlist strip, no Pillow

Amended after the fourth architect FAIL (2026-11-26). The earlier design
re-encoded with Pillow from a uv script. Pillow is not reliably there, so the
helper now needs nothing beyond `python3`.

**Where Pillow is, measured on 2026-11-26:**

| Place | Pillow? | Source |
|---|---|---|
| The image the factory runs, `habitat-worker:1840e163…` | **no** | `agents/factory.yml:39` pins it; habitat `git show 1840e163:worker/Containerfile` installs `git ca-certificates jq python3 shellcheck` and a Playwright venv, no Pillow |
| habitat `868608bf…` (designer role, not used by this factory) | Pillow `12.0.0` in `/opt/habitat/design-venv` only | habitat `worker/Containerfile` at `868608b` ("Add a designer role", #56). Not on the default `python3`, outside the old `pillow>=11,<12` pin, and absent from CI and agent-lxc |
| The cage at run time | only if `uv` reaches PyPI during the run (every pod starts with an empty uv cache) | habitat `cage/ciliumnetworkpolicy.yaml` allows `pypi.org` and `files.pythonhosted.org` on 443. The 2026-11-25 builder run of this change reported "Pillow 11.3.0 resolves" |
| agent-lxc offline | **no**, for the old pin | `uv run --offline --with 'pillow>=11,<12'` fails ("the network is disabled"); the cache holds 12.3.0 and 13.0.0 only |
| CI | only over the network | `.github/workflows/verify.yml` runs `uv run --with pyyaml bash verify.sh`; no Pillow anywhere |
| ratatoskr itself | no dependency file at all | no `pyproject.toml`, `uv.lock` or `requirements*.txt`. Dependencies are per-script PEP 723 blocks resolved by `uv run` (`orchestrator/push-notify.py`: pywebpush). The chat image is stdlib-only (`chat/Dockerfile:40-41`). The listener runs as `agents/run.sh` under systemd |

So Pillow would arrive over the network, on every build, in every CI run and
in every pre-push `verify.sh`. `verify.sh` says it must stay green offline
(line 4). The strip test would have been the only test in it that needs PyPI.

**Threat model.** The helper removes *accidental* metadata, the kind a camera,
an editor or an encoder writes. A sender who hides data on purpose is out of
scope, because pixels can carry anything.

**What the helper does instead.** It keeps the pixel data byte for byte and
throws away every container part that is not on a short keep-list. Nothing is
decoded and nothing is re-encoded.

**Files and line budget.** All files are stdlib-only, have an SPDX header and
stay at 200 lines or fewer (`scripts/line_limit.py`). Where the lines go is
fixed in advance, so no file has to be split during the build:

| File | Holds | Budget |
|---|---|---|
| `orchestrator/image_strip.py` | the three walkers, keep-lists and exact-length checks | ≤ 200 |
| `orchestrator/image_exif.py` | the Exif/TIFF reader: IFD0 tag `0x0112` | ≤ 80 |
| `orchestrator/image_prep.py` | `prepare(data) -> (bytes, ext)` raising `Refused(reason)`, magic bytes, limits, the catch-all, and the CLI | ≤ 120 |
| `orchestrator/image_testwalk.py` | the tests' own independent walkers (not `test_*`, so discovery does not run it as a test) | ≤ 150 |
| `orchestrator/test_image_strip.py` | per-fixture keep paths, refusal paths | ≤ 200 |
| `orchestrator/test_image_prep.py` | the CLI, limits, orientation, the agent-facing messages | ≤ 200 |
| `orchestrator/test_image_robust.py` | truncation and byte-flip sweep | ≤ 120 |
| `orchestrator/test_image_fixtures.py` | the sha256 check of `orchestrator/testdata/SHA256SUMS` | ≤ 40 |

The CLI is `python3 orchestrator/image_prep.py <src> <outdir>`. Every refusal
prints `image_prep: <reason>` on stderr, exits 2 and writes nothing.

Steps, in this order:

1. `src` must be a regular file. It is read with a cap,
   `f.read(LIMIT + 1)` with `LIMIT = 20 MiB`, and more than `LIMIT` bytes is
   refused. There is no stat-then-read.
2. Magic bytes: PNG `89 50 4E 47 0D 0A 1A 0A`, JPEG `FF D8 FF`, WebP
   `RIFF????WEBP`. The extension is never consulted. GIF (`GIF8`), SVG or XML
   (`<svg`/`<?xml` after leading whitespace), HEIC/AVIF (`ftyp` at offset 4)
   and PDF (`%PDF`) are refused by name. Anything else is refused as
   "unknown file type".
3. Walk the container under the parsing rules and keep-lists below.
4. Dimensions (rules below). Either side over 2560 px is refused with a
   message for agents:
   `image_prep: 2880x1800 exceeds 2560 px per side; make it smaller at the
   source (Playwright: no fullPage, viewport or clip <= 2560, scale: "css";
   matplotlib: figsize x dpi <= 2560)`.
5. **Orientation.** `image_exif.py` reads every Exif block the walk drops
   (JPEG APP1 `Exif\0\0`, PNG `eXIf`, WebP `EXIF` with or without the
   `Exif\0\0` prefix) for IFD0 tag `0x0112`. A value other than 1 is refused
   with "EXIF orientation <n>: rotate the pixels before sending", because
   dropping the block without that check would show the picture sideways (a
   silent failure). An unreadable Exif block (a bad byte order, an offset past
   the end, a truncated IFD) is refused. An Exif block without an Orientation
   tag is accepted.
6. The output is ≤ 5 MiB. If not, it is refused with the size and the limit.
7. Self-check: the output is walked again, and every part must be on the
   keep-list. Otherwise: "strip self-check failed: <part>". That would be a bug,
   not an input problem.
8. The helper writes `<outdir>/image.<png|jpg|webp>` (the extension comes from
   the magic bytes), prints that path and exits 0.

**Bounded parsing and clean failure.**

- **Every walker step moves forward.** Each loop iteration checks that the new
  position is greater than the old one, and refuses otherwise. Every length is
  checked against the end of the data before it is used.
- **The catch-all.** `prepare` wraps the walk: any `struct.error`,
  `IndexError` or `ValueError` becomes `Refused("cannot parse <fmt>: <exception
  text>")`, so the CLI prints `image_prep: cannot parse <fmt>: …` and exits 2.
  The CLI never shows a traceback. Anything else is a bug and stays loud.
- **Duplicates are refused:** a second IHDR, PLTE, tRNS or IEND; a second SOF,
  SOI or EOI before the end; a second VP8X, ALPH or image chunk.
- **Exact lengths (hardening).** A kept part must be exactly as long as its
  contents say:
  - DQT: the sum over its tables of `1 + 64 × (1 + Pq)`.
  - DHT: the sum over its tables of `1 + 16 + Σ counts`.
  - SOF: `6 + 3 × Nf`.
  - The SOS header: `4 + 2 × Ns`.
  - DRI: 2 bytes.
  - IHDR: 13 bytes.
  - PLTE: a multiple of 3, at most 256 entries.
  - tRNS: 2 bytes for colour type 0, 6 for type 2, at most the PLTE entry
    count for type 3, and refused for types 4 and 6.

  A mismatch is refused, so nothing can ride inside a kept part's slack.

**Dimensions.**

- **PNG:** IHDR is the first chunk, exactly once, with 13 bytes. Width and
  height are both non-zero.
- **JPEG:** exactly one SOF. Width and height are non-zero; a height of 0
  means a DNL marker, which is not supported.
- **WebP:** the VP8 frame header (after the start code `9D 01 2A`, 14-bit
  width and height) or the VP8L header (signature `0x2F`, 14-bit width−1 and
  height−1) is **always** read. When a VP8X is present, its canvas must equal
  the frame size, or the image is refused.

Keep-lists. Everything not listed is dropped, apart from the refusals named
here:

- **PNG.** Keep `IHDR`, `PLTE`, `tRNS`, `IDAT` and `IEND` byte for byte
  (length, type, data, CRC), in their order. The CRC is verified on every
  chunk. Drop every other ancillary chunk: `tEXt`, `zTXt`, `iTXt`, `eXIf`,
  `iCCP`, `gAMA`, `cHRM`, `sRGB`, `pHYs`, `tIME`, `bKGD`, `sBIT`, `hIST`,
  `sPLT` and private chunks. **APNG is refused**: any `acTL`, `fcTL` or `fdAT`
  gives "animated PNG", as animated WebP does. An unknown *critical* chunk
  (first letter upper case) is refused. Bytes after `IEND` are dropped.
- **JPEG.** The output is `SOI`, then one canonical JFIF APP0 (`FF E0 00 10
  4A 46 49 46 00 01 01 00 00 01 00 01 00 00`: no thumbnail), then the kept
  segments in their original order, then `EOI`.
  - **Markers.** Between segments, `FF` fill bytes are skipped. A byte other
    than `FF` where a marker is expected is refused, never copied. A segment
    length below 2 is refused.
  - **Kept:** `DQT`, `DHT`, `DRI`, `SOF0`/`SOF1`/`SOF2`, and `SOS` with its
    entropy-coded data. The scan runs until an `FF` that is followed by
    neither `00` nor `D0`–`D7`, so the RST markers stay inside the scan. The
    walk then goes on, because a progressive file has many scans.
  - **Dropped:** `APP0`–`APP13`, `APP15` and `COM`, wherever they are,
    including between scans. Bytes after `EOI` are dropped too.
  - **Refused:**
    - `APP14`. It is an Adobe colour transform, so dropping it would change
      the colours. The message tells the agent to re-save as PNG.
    - A 3-component SOF whose component IDs are `R`, `G`, `B` (`0x52 0x47
      0x42`). Without APP14 it is coded as RGB, and inserting JFIF would
      relabel it as YCbCr and change its colours.
    - A component count other than 1 or 3, with or without APP14.
    - Every other `SOFn`, such as `SOF3` (lossless) or `SOF9` (arithmetic).
      No browser shows them.
    - Any marker not named here.
- **WebP.** Walk the RIFF chunks (little-endian sizes, padded to an even
  length).
  - **Refused:** a RIFF size other than the file length minus 8, a chunk past
    the end, `ANIM`, `ANMF` or the VP8X animation flag even without `ANIM`
    ("animated WebP"), `ALPH` next to `VP8L`, and more than one image chunk.
  - **Without `ALPH`:** the output is the simple format, `RIFF`, the new
    size, `WEBP`, and the single `VP8 ` or `VP8L` chunk byte for byte.
  - **With `ALPH`** (lossy with alpha): a `VP8X` with flags `0x10` (alpha
    only) and the canvas size (equal to the frame), then `ALPH` and `VP8 `
    byte for byte.
  - **Dropped:** `ICCP`, `EXIF`, `XMP ` and unknown chunks.

This approach was prototyped on 2026-11-26 against the committed fixtures,
including `dirty-restart.jpg`. A throwaway script of about 60 lines, not
committed, ran the keep-lists above, and Pillow 13 decoded every output to
pixels identical to the input, with no Exif, XMP, ICC, comment or Photoshop
data left. The builder writes the real code; the prototype only shows that
the keep-lists lose no pixels.

The relay refuses metadata on its own (422, measured), so a file that slips
past the helper is stopped there too. That is defence in depth, not the plan.

The earlier rejection of stdlib stripping was that hand parsing "looks right
while it keeps an APP1" (#223). Five things answer it:

- The parser uses a keep-list, so an unknown part is dropped or refused, never
  kept by mistake.
- Kept parts must have their exact lengths.
- The output is walked again by the helper itself.
- The tests walk the output with their own independent parser, after first
  proving that every input is dirty, and compare the image data byte for byte.
- A truncation and byte-flip sweep shows that the walk fails cleanly.

Rejected:
- **Pillow through `uv` at run time** (the earlier design). It is not in the
  factory's image and would arrive from PyPI on every build, CI run and
  pre-push `verify.sh`, while `verify.sh` must stay green offline. The third
  and the fourth architect FAIL both found a gap here.
- **Bumping the factory to `868608bf` and using its design venv.** That ties a
  ratatoskr test to habitat's designer path `/opt/habitat/design-venv`, which
  does not exist in CI or on agent-lxc, at Pillow 12. A factory image bump is
  also a change of its own.
- **Re-encoding with a tool that is present.** The worker image has
  `rsvg-convert` (SVG in, so no use here) and a Chromium headless shell in the
  playtest venv. agent-lxc has no ImageMagick, `cwebp`, `cjpeg` or `exiftool`
  (`which` finds none). CI has none of them. No tool is present in all three
  places.
- **Refusing every image that carries metadata.** Detection needs the same
  walk, so it saves no parser. It would also refuse the main use case:
  matplotlib writes a `tEXt` "Software" chunk into every chart, and agents
  have no tool to strip it themselves.
- **Fitting the image inside 2560 px.** That needs a decoder. The helper
  refuses a larger image instead. Agents make their screenshots and charts
  themselves (Playwright viewport, matplotlib dpi), so they can make them at
  the right size.
- **Vendoring Pillow wheels.** A binary blob in git, for a dependency that is
  then also tied to one platform.
- **Stripping in the chat.** Still rejected: it would put a dependency or the
  same parser into the deliberately stdlib-only chat image.

### The helper is `ping.sh`, extended

```
IDENT=architect CHAN=architectuur orchestrator/ping.sh --image chart.png 'p95 latency, last 7 days'
```

`--image <path>` has to be the first argument, and the caption is the third.
A caption is required, because the notification and the `alt` text need one.
Everything else in `ping.sh` stays as it is: IDENT lookup, the human identity
refused, inactive identities refused, `#general` hub-only for sessions, and the
nsec from SOPS. In order:

1. Argument parsing (line 14) branches: with `--image`, `IMG=$2` and
   `MSG=${3:-}`, and an empty caption exits 9. Without it, `MSG="${1:-$(cat)}"`
   as today.
2. The IDENT and channel checks (lines 20-46) run unchanged, so a human or
   inactive IDENT is refused before anything touches the image.
3. With `--image`: `TMP=$(mktemp -d)` with `trap 'rm -rf "$TMP"' EXIT` (the
   `jobs/publish-board.sh:13-14` pattern), then
   `OUT=$(python3 "$ROOT/orchestrator/image_prep.py" "$IMG" "$TMP") || { echo
   "[ping] image refused (image_prep.py)" >&2; exit 10; }`. The `||` is needed
   because `set -e` would otherwise exit with the helper's 2. The helper's own
   reason is already on stderr. This happens **before** the
   `sops -d` on line 47, so a refused image never decrypts a key.
4. The send. The image branch runs `buzz messages send --channel "$CID"
   --content "$MSG" --file "$OUT" --mention "$NPUB"`. That is the form gate 1.1
   measured, plus the `--mention` that every `ping.sh` message carries. It
   does not keep the text path's `--content -` (stdin), because stdin together
   with `--file` was never measured. **`--mention` stays**, since the
   identity-registry delta says every existing behaviour applies unchanged.
   Gate 3.1 is the live proof of the three flags together. If the real CLI
   refuses them there, the fallback is fixed: drop `--mention` on the image
   branch only, and record that in design.md. The text-only branch does not
   change.

**On exit 10 the agent has two ways on, and the docs name both:** crop or
shrink the image at its source and send again, or send a text ping that
describes it. A refused image never blocks the report itself.

`ping.sh` calls `~/.local/bin/buzz` by a fixed path, not through `PATH`. Its
test therefore gives it a fake `HOME` that holds `.local/bin/buzz`, and a fake
`sops` on `PATH`. `uv` is not used on the image path at all.

All new interface text is English (AGENTS.md "Nieuw werk meteen Engels",
ADR-0001): the stderr messages for exits 9 and 10 in `ping.sh`, and the log and
failure messages of `jobs/prune-media.sh`. The loud failure of the size check
keeps its meaning: the total is over the limit of `MEDIA_MAX_BYTES`, busier
than expected, and that is not deliberate growth. Pre-existing Dutch text in
these files is not translated here; that stays in the separate translation
change.

Rejected: **a separate `ratatoskr-send` CLI**. It would be a second post path,
and the identity rules would have to be kept equal in two places. That is how
an impersonation guard ends up missing from one of them.

### Settled by the architect's findings (ratatoskr#260, third FAIL)

1. **The tags travel through the cooldown.** `notify._last` stores
   `(author, content)` for the held-back message and `flush` rebuilds the push
   from that pair, so tags passed only to `push` are gone for any message the
   cooldown held. `_last` now stores the tags with the message, and `flush`
   hands them to the same body builder `push` uses. A seam test calls both
   sides: `push` inside the cooldown, then `flush` after it, asserting the
   delivered body is `🖼 <caption>`.
   Rejected: *tags on the `push` path only* (a held-back image would notify as
   its Markdown line, which is the silent kind of wrong AGENTS.md names);
   *computing the body at `push` time and storing the string* (the "+n eerder"
   suffix is only known at flush, so the body must be built there).
2. **Pillow offline** (superseded on 2026-11-26). The guard test that told
   "no network" from "broken code" is gone, together with Pillow: the helper
   and its tests are stdlib-only, so there is nothing left to resolve. See
   "Preparing the image".
3. **One parser, one fixture.** Caption and `imeta` parsing exists once, in
   `chat/imeta.py`, tested against `chat/testdata/imeta-event.json`. The
   notification uses it here, and `agent-image-to-chat-read` reuses it for
   `images` and the cleaned content instead of writing a second parser. Where
   it lives and how `agents/` loads it is settled below (fourth FAIL, gap 7).
   Rejected: *a parser in `notify.py` and another in `chat/`* (two readers of
   one tag format drift apart, and only one fixture would pin them);
   *a second fixture for the chat* (the same event, copied).
4. **Blob dedup versus age is accepted.** If the relay does not store a blob it
   already has, an image re-sent on day 29 is pruned a day later and its new
   message shows "expired". Rejected: *tracking last-referenced time per blob*
   (an inventory and an ordering for a rare case, the same cost that rules out
   oldest-first eviction below); *a longer retention* (changes Mark's decided
   30 days). Mark's rule is "a picture lives 30 days"; the text stays.

The split stays: this build is A plus C. The read path remains
`agent-image-to-chat-read`, behind Gate 0.

### Settled by the architect's findings (2026-11-26, fourth FAIL)

The fourth run failed on two points, both about the evidence for the
metadata strip: the test runner (gap 1) and where the fixtures come from
(gap 2). It listed seven gaps and six risks in all. Each is settled here, so
the builder does not have to resolve any of them on its own.

1. **Runner.** The repo has no pytest. `verify.sh:10-13` and CI
   (`verify.yml:28`, through `verify.sh`) run `python3 -m unittest discover -p
   "test_*.py"` per directory. Every new test is a `unittest.TestCase`
   method, with no bare `def test_*`, no `conftest`, no pytest, and no
   `skipTest` in the image tests. There is no host step to wire up: discovery
   already picks up `orchestrator/test_image_*.py`.
2. **Fixture origin.** The metadata-bearing inputs are committed in this
   amend, under `orchestrator/testdata/` (table under "Tests"), together with
   their generator `orchestrator/testdata/make_image_fixtures.py`. That
   generator is a host-only uv script: Pillow encodes a clean 24×16 base, and
   every piece of metadata is added by stdlib byte surgery. The build, CI and
   `verify.sh` never run it; the tests only read the bytes. The cases that are
   easy to make (truncated, a bad CRC, a header claiming 20000×20000, an
   oversized file, SVG or GIF bytes behind a `.png` name) are built inside the
   tests with stdlib. No binary over 2 KiB enters git.
3. **Each input is proven dirty.** Before a test asserts that an output is
   clean, it asserts that the input carries the metadata the fixture table
   lists, using the test's own walker. Every dirty fixture also carries the
   sentinel `fixture-` (author, comment and ICC strings), which must be in the
   input and absent from the output.
4. **Exit condition.** `uv run --with pyyaml bash verify.sh` (the CI command)
   is green, all of it, in the cage and in CI. There is no exception and no
   skip. Nothing this change adds needs the network or the host. The image
   tests are stdlib-only. `pyyaml` is the dependency `verify.sh` and
   `ping.sh` (the `identities.yml` lookup) already have, and it comes in the
   way it does today. On
   agent-lxc the unit split below keeps the `units` and `timers` steps green.
5. **`--mention` on the image branch.** It stays, is pinned in 2.2's argv test,
   and gate 3.1 has a fixed fallback (see "The helper is `ping.sh`").
6. **The prune units and the local gate.** `scripts/check_units.py` reports
   every unit in `jobs/systemd/` that is missing from `~/.config/systemd/user`,
   so between merge and enabling, `verify.sh` would be red on agent-lxc. 3.3
   is therefore split. Right after the merge, the unit **files** are installed
   with `python3 scripts/check_units.py --install`, which copies them and runs
   `daemon-reload` but enables nothing. Only after gate 1.2 come `systemctl
   --user enable --now ratatoskr-media-prune.timer` and one run of the
   service. This was measured on agent-lxc on 2026-11-26: a timer installed in
   `~/.config/systemd/user` and not enabled is **not** listed by `systemctl
   --user list-timers --all`, so `scripts/check_timers.py` (which reads only
   that list) stays green. The one run is needed because an enabled service
   that never ran has an empty `ExecMainStatus`, and `fouten()` flags that.
   If gate 1.2 finds the filter unsafe, the files stay installed and
   disabled, and both checks stay green.
7. **Helper location.** `chat/imeta.py`, stdlib-only, with an SPDX header.
   `chat/Dockerfile:40` copies `chat/` to `/app/`, so the chat image and the
   follow-up get it, and line 41 strips `test_*.py`, so `chat/test_imeta.py`
   does not ship. Its interface is `from_tags(tags) -> list[dict]` (one dict
   per `imeta` tag whose `m` starts with `image/`, with keys `url`, `m`, `x`,
   `size`, `dim`) and `clean_content(content, tags) -> str` (removes, for each
   image URL, the whole `![image](<url>)` line with its leading newline, then
   strips). **Neither function ever raises.** Tags that are not a list, an
   entry that is not a list, an `imeta` entry with no fields, non-string
   fields, or a field without a space are skipped. `from_tags` then returns
   `[]`, `clean_content` returns the content unchanged, and the push falls
   back to plain text. `agents/notify.py` loads it **by file path** with
   `importlib.util.spec_from_file_location("imeta", <ROOT>/chat/imeta.py)`,
   not by putting `chat/` on `sys.path`. Both `chat/board.py` and
   `orchestrator/board.py` exist, and `agents/factory_wiring.py:28` already
   puts `orchestrator/` on the listener's path, so a second path entry would
   make `import board` depend on the order. Rejected: *`sys.path.insert` of
   `chat/`* (that name clash); *a copy in `agents/`* (a second parser); *a
   top-level package* (the chat image copies `chat/` only).

Risks from the same run:

- **Pillow in the cage**: gone, see gap 4. Nothing this change adds resolves
  a package.
- **`agents/listener.py` at exactly 200 lines** (the baseline file holds only
  its header): settled under "Notification". The listener gets **shorter**.
- **Blob dedup versus age**: accepted, decision 4 above.
- **Gate 1.2 may make the `--include` filter unsafe**: then the prune stays
  disabled with a `waiting-on-mark` issue and the hash-list default (gate 2).
  Gap 6 keeps the local gate green in that state.
- **Images unseen until the follow-up**: accepted. It is the one thing to say
  to Mark at merge (task 3.5).
- **Probe blobs**: the three probe blobs are deleted by the first prune, which
  is intended.

### Review of #267 (2026-11-26)

The review of this amend asked for more before the build. Each point is now in
this design:

- **Bounded parsing:** see "Bounded parsing and clean failure" (forward
  progress, JPEG lengths below 2 and non-`FF` bytes refused, fill bytes
  skipped, the `cannot parse` catch-all). Tests: `test_image_robust.py` and
  the refusal list under "Tests".
- **Dimensions** (always from the frame, VP8X equal to it, one SOF with a
  non-zero height, IHDR first, once and 13 bytes, duplicates refused): see
  "Dimensions".
- **Malformed imeta tags:** `from_tags` never raises (gap 7), and
  `on_message` has a second layer (see "Notification").
- **Threat model and exact lengths:** at the top of "What the helper does".
- **APNG refused**, and **RGB-coded JPEG refused**, with APP14 telling the
  agent to re-save as PNG: see the keep-lists.
- **Untested keep paths:** a palette PNG (built in the test) and
  `dirty-restart.jpg` (DRI with RST markers).
- **Line budget:** the file table under "Files and line budget".
- **Small points:** the generator is pinned to `pillow==13.0.0` and writes
  `SHA256SUMS`, which `test_image_fixtures.py` checks; the input is read with
  `read(LIMIT + 1)`.
- **The 2560 px refusal for agents:** the message in step 4, a spec scenario,
  and the exit-10 fallback under "The helper is `ping.sh`".

### Notification: text, with a marker

`agents/listener.py` is at exactly 200 lines, the hard limit, and
`scripts/line_limit_baseline.txt` holds only its header, so the file may not
grow. Instead of adding a fourth argument, the decision moves out of the
listener:

- **What moves.** Lines 161-162 (`if notify.should_notify(cname, writer,
  m.get("content", ""), ME_NAME):` and `notify.push(cname, writer,
  m.get("content", ""))`) become one line, `notify.on_message(cname, writer,
  m, ME_NAME)`. The listener goes to 199 lines. Reading `content` and `tags`
  from the relay event, and the should-notify test, now live in
  `agents/notify.py`.
- **`notify.on_message(cname, author, event, me)`** takes the event dict as
  `relay.get_messages` returns it (`buzz messages get`), which is the same
  shape as `chat/testdata/imeta-event.json`. It returns `False` when
  `should_notify` says no, and otherwise `push(cname, author, content,
  tags)`.
- **`push(cname, author, content, tags=None)`.** The default keeps every
  existing caller and test working. `_last[cname]` stays `(t, missed, held)`,
  and `held` becomes `(author, content, tags)`, so `agents/test_notify.py`
  lines 50, 57 and 66, which read `_last[cname][0]`, keep their meaning.
  `flush` unpacks the triple. `push` and `flush` both call `_body(content,
  missed, tags)`. When `imeta.from_tags(tags)` is non-empty, the body is
  `🖼 ` plus `imeta.clean_content(content, tags)`, or `🖼 image` when that is
  empty. Then the existing 140-character cut and the `+n eerder` suffix
  apply. Nothing changes for a message without an image `imeta` tag.
- **A second layer for malformed tags.** `imeta` never raises (gap 7). On top
  of that, `on_message` builds the push inside `try`/`except Exception`. On an
  exception it prints `[listener] notify: image tags unreadable (<reason>)`
  and pushes the plain-text body, so a bad event never costs the
  notification and never stops the listener loop. This fits the budget:
  `notify.py` is at 102 lines.

This touches the **Web Push** chain, the first of AGENTS.md's four silent
chains (notify → `orchestrator/push-notify.py` → VAPID → phone). Its tests:

- `agents/test_notify.py`, with `subprocess.run` patched (not `_send`), so the
  real argv to `push-notify.py` is what gets asserted:
  `on_message` with the fixture event gives `--body "🖼 gate 1.1 imeta probe
  (#243) — 16x16 test image, deleted right after"`, with no `![image]` and no
  `/media/` in it. In the **seam case**, `on_message` sends a first message,
  the fixture event arrives inside the cooldown (held), and then `flush(now=…)`
  is called after the cooldown. The flushed `--body` is the same `🖼` line. The
  builder checks that this case **fails** when `held` is reduced back to
  `(author, content)`, and says so in the PR. A plain-text twin pins that the
  body of a message without an image is unchanged. Another case pins that
  `should_notify` still filters (`#statistics`, own message, `⋯`).
  Malformed tags are covered too: `["imeta"]`, `["imeta", 7]`,
  `[["imeta", None]]`, tags as a string, tags as a dict, and `tags` missing.
  Each gives the plain-text body, and none raises.
- **The listener side of the seam**, pinned the way
  `agents/test_build_starters.py:119-127` already pins `build_starters.take`:
  a test reads `agents/listener.py` and asserts that it contains
  `notify.on_message(cname, writer, m, ME_NAME)` once, and no `notify.push(`
  or `notify.should_notify(`, and also not the stale comment name
  `notify.should_notify` (the comment at `agents/listener.py:159` is rewritten
  to `notify.on_message` in the same edit). A later edit that goes back to
  passing `content` alone fails there.
- `chat/test_imeta.py`: `from_tags` and `clean_content` against the same
  fixture, plus the same malformed shapes (each gives `[]` and an unchanged
  content, without raising).
- Unchanged, and still green: `orchestrator/test_push_chain.py` and
  `orchestrator/test_push_send.py`. `push-notify.py` is not touched, and the
  body still travels as `--body`. `chat/e2e/push-states.js` is not affected
  (no service worker or chat change), and gate 4 (task 3.4) is the live end
  of the chain.

The push payload stays text (Web Push payloads are about 4 KiB), and a tap
opens `/#<channel>`.

Rejected: *the fourth argument on line 162* (it fits the line count, but it
leaves the event-to-push seam in a 200-line file that has no unit test, and
the next change there has no line to spare); *passing `m` to `push`*
(`push` would then know the relay's event format as well as the cooldown);
*a second listener module for the notify branch* (a new file for two lines).

A picture *inside* the notification needs the `image` option of
`showNotification`, and that image has to come from a session-gated URL. Chrome
loads notification images itself, and whether it sends the session cookie
there is unknown. The service worker could fetch the image and pass a `data:`
URL instead, but that touches the push chain, which AGENTS.md lists among the
four chains that get no line of code without their own tests. It is therefore a
gate to measure and a decision for Mark, not part of this build.

### Retention: 30 days, then gone; loud above 2 GiB

- **What:** blobs in `buzz-media` whose key ends in `.png`, `.jpg`, `.jpeg` or
  `.webp` (this includes the relay's `.thumb.jpg`) and that are older than 30
  days.
- **How:** a new compose service `media-prune` under `profiles:
  ["maintenance"]`, so `docker compose up` never starts it. It uses the
  `rclone/rclone:1.71` image already pinned for `seaweedfs-init`, with the same
  `RCLONE_CONFIG_DST_*` environment. Its command is
  `delete dst:${BUZZ_S3_BUCKET:-buzz-media} --min-age 30d --include
  "*.{png,jpg,jpeg,webp}" -v`. `jobs/prune-media.sh` on agent-lxc runs it over
  ssh: `ssh buzz-relay 'cd /opt/buzz-relay && sudo docker compose --profile
  maintenance run --rm media-prune'`, the same ssh+sudo route
  `publish-board.sh` takes. It then runs `… run --rm media-prune size
  dst:buzz-media --json` and exits 1 when the total is above `MEDIA_MAX_BYTES`
  (default 2 GiB).
- **When:** `jobs/systemd/ratatoskr-media-prune.{service,timer}`, daily at
  04:30, `Persistent=true` (a missed day should still run). The files are
  installed right after the merge and enabled only after gate 1.2 (fourth
  FAIL, gap 6).
- **Why loud:** a failing timer is caught by `scripts/check_timers.py`, and it
  shows in Mark's digest as an impediment once it has failed for 12 hours. A
  size alarm that only writes a log line would be the silent failure that
  AGENTS.md forbids.
- **Expected volume:** 5 MiB is the ceiling and a screenshot within 2560 px is
  typically 0.3–1.5 MiB. Twenty images a day for 30 days is about
  0.6 GiB, so 2 GiB means something is wrong, not that things are busy.
- **After the prune:** the message text stays. What the chat shows for a pruned
  image is the follow-up's (410, "image expired (kept 30 days)").

Rejected:
- **Never prune.** #223's trap: the store is append-only by construction.
- **A bucket lifecycle rule in SeaweedFS.** It is invisible in git, support
  through the S3 API is unverified, and it applies to the whole bucket.
- **Blossom DELETE signed by the uploader.** The CLI has no delete, and the
  uploader's key lives on another host than the store.
- **A cap per volume with oldest-first eviction.** That needs an inventory and
  an ordering, which is more code for the same outcome. An age is easier to
  state to Mark ("a picture lives 30 days").

## Handed to `agent-image-to-chat-read`

Not requirements of this change. This is what the follow-up's design.md starts
from; it is built only after its Gate 0 is recorded there.

- **Gate 0 (host, first).** Measure on the chat container's CLI
  (`BUZZ_REF=4baccd53…`, `chat/Dockerfile:12`), via `docker run --entrypoint
  buzz` or `docker compose exec chat`, not on agent-lxc's
  `~/.local/bin/buzz`. Record the CLI version and **the exact `buzz media get`
  invocation, including the flag that sends the bytes to stdout.** `-o -` is
  unverified: do not assume it; if the CLI has no stdout form, the design
  changes (for example a temp file). Then record (a) that invocation as `mark`
  on the blob from gate 1, byte-identical; (b) the same on a blob uploaded by
  `odin`; (c) an unknown hash giving 404. If a `BUZZ_REF` bump is needed,
  `relay-deployment/spec.md:38` forces a relay image bump, which is its own
  change.
- **Route `GET /api/media/<sha256>`**, behind `auth_routes.gate(...,
  writes=False)`: 400 unless 64 lowercase hex; 410 `image expired (kept 30
  days)` on buzz 404; 502 with the reason (200 chars) on any other failure,
  timeout (25 s) or a blob over 5 MiB (read with a ceiling); 415 unless the
  magic bytes are PNG, JPEG or WebP; 200 with `Content-Type` from the magic
  bytes, `X-Content-Type-Options: nosniff`, `Content-Security-Policy:
  default-src 'none'; sandbox`, `Cache-Control: no-store`, `Content-Disposition:
  inline`. `chat/media.py` runs the CLI with bytes output itself, because
  `buzzcli.buzz()` uses `text=True`.
- **The headers sender must be designed, not assumed.** `chat/server.py:28-42`
  `_send` cannot emit `Cache-Control`, `X-Content-Type-Options`,
  `Content-Security-Policy` or `Content-Disposition`. The follow-up adds an
  extension of `_send` that takes extra headers, with a pinned test that calls
  both sides: the route producing the headers and `_send` writing them to the
  socket, asserting all four on the wire.
- **`/api/messages` `images`**, parsed from `imeta` (`from_tags`,
  `clean_content`), driven by `chat/testdata/imeta-event.json`; the UI
  (`chat/app-image.js`, `chat/image.css`, the hook line 148 of `chat/app.js`,
  `sw.js` `v33`, chat pin `0.19.0` / `chat-v0.19.0`); `chat/test_media_seam.py`;
  `chat/e2e/image.js`; the troubleshooting section on 410 versus 502; and the
  `webchat-pwa` requirements for the image view and the response headers.
- **After a prune** (needs the prune timer live): `buzz media get` on a deleted
  hash returns 404, not a 500 from a dangling row. Otherwise the chat maps it
  to "relay error".

## Gates (before or during the build)

1. **imeta shape (host). Done 2026-11-24**, see "Measured on 2026-11-24". It
   is the only gate the build waits on. The recorded event is committed as
   `chat/testdata/imeta-event.json`.
2. **Bucket inventory (host, before enabling the timer).** Run `docker compose
   run --rm media-prune lsf dst:buzz-media` and record the key layout and every
   key that is not an image. If keys have no extension, or something other than
   chat media lives there (custom emoji, avatars, persona packs), the
   `--include` filter is not safe. The timer then stays disabled and a
   `waiting-on-mark` issue says so. Default in that case: prune by a list of
   hashes collected from the `imeta` tags of messages older than 30 days.
3. **PNG, JPEG and WebP through the relay (live, task 3.1).** Send one
   helper-prepared file of each kind through the real `ping.sh --image`: the
   stripped `dirty.png`, `dirty.jpg`, `dirty-lossless.webp` (simple `VP8L`)
   and `dirty-lossy-alpha.webp` (`VP8X` + `ALPH`). This proves that the real CLI takes `--content '<caption>' --file
   <path> --mention <npub>` and that the relay's metadata check accepts what
   the helper writes. Each format has a fixed fallback if the relay refuses
   it (422). For JPEG, drop the canonical JFIF APP0 as well, since a JPEG
   without APP0 is valid. For a WebP with alpha, refuse `ALPH` in the helper
   (lossy with alpha is then refused by name, and lossless with alpha still
   works through simple `VP8L`). If the simple `VP8L` is refused too, the
   helper refuses WebP by name and PNG and JPEG remain. For PNG nothing changes: only
   `IHDR/IDAT/IEND` was accepted on 2026-11-13. For the CLI flags, drop
   `--mention` on the image branch. Each fallback is a change of a few lines
   with its test, recorded in design.md.
4. **On the phone (live).** The `🖼 caption` notification shows and a tap opens
   the channel. Separately, record whether a `showNotification` with an `image`
   (a `data:` URL built by the SW) shows on Mark's Android. Record only; do not
   build it.

## Tests

All tests are `unittest.TestCase` classes, discovered by `verify.sh` and CI
as they are today. None needs the network, Pillow, the relay or SOPS. The image
test files are stdlib-only and contain no `skipTest`. `test_ping_image.py`
runs `ping.sh`, which reads `identities.yml` with `pyyaml`, as it does today.

**Committed fixtures** (`orchestrator/testdata/`, 24×16, each under 1.3 KiB).
They are written by `make_image_fixtures.py`, pinned to `pillow==13.0.0`,
which also writes `SHA256SUMS`. There are seven dirty fixtures, two rotated,
one CMYK and one animated. Every dirty fixture contains the sentinel
`fixture-` and the GPS IFD (52° 22′ N). Pillow 13 reads their Exif, XMP and
ICC data, which is how they were checked on 2026-11-26.

| File | Carries | Expected |
|---|---|---|
| `dirty.png` | `gAMA`, `iCCP`, `pHYs`, `tEXt`, `zTXt`, `iTXt` (XMP), `eXIf` (Orientation 1 + GPS), `tIME`, two `IDAT`, private `prVt` | only `IHDR`, `IDAT`, `IDAT`, `IEND`, byte-identical |
| `rotated.png` | as `dirty.png`, Orientation 6 | refused: `orientation 6` |
| `dirty.jpg` | JFIF APP0 with a thumbnail, APP1 Exif (Orientation 1 + GPS), APP1 XMP, APP2 ICC, APP13 Photoshop/IPTC, COM, bytes after EOI | SOI, canonical JFIF, then DQT/SOF0/DHT/SOS+scan byte-identical, EOI |
| `dirty-progressive.jpg` | as `dirty.jpg`, progressive (SOF2, ten scans), a COM **between** two scans | as above, all scans kept, both COMs gone |
| `dirty-restart.jpg` | as `dirty.jpg`, 4:4:4 with `restart_marker_blocks=1`: a DRI and RST0–RST4 inside the scan | DRI kept, the scan with its five RST markers byte-identical |
| `rotated.jpg` | as `dirty.jpg`, Orientation 6 | refused: `orientation 6` |
| `cmyk.jpg` | four components, Adobe APP14 | refused: `APP14`, with "re-save as PNG" |
| `dirty-lossy.webp` | VP8X (ICC/EXIF/XMP flags), `ICCP`, `VP8 `, `EXIF`, `XMP `, unknown `fxTR` | simple `RIFF/WEBP/VP8 `, chunk byte-identical |
| `dirty-lossless.webp` | the same around `VP8L` | simple `RIFF/WEBP/VP8L` |
| `dirty-lossy-alpha.webp` | the same with `ALPH` + `VP8 ` | `VP8X` flags `0x10`, `ALPH`, `VP8 ` byte-identical |
| `animated.webp` | `ANIM` + two `ANMF` | refused: `animated` |

**Built inside the tests** (stdlib, from the fixtures or from scratch). Each
case asserts its outcome, and each refusal names its reason:

- **PNG:**
  - a **palette PNG** with `PLTE` and `tRNS` plus a `tEXt`, which is kept
    with PLTE and tRNS byte-identical and the tEXt gone;
  - one flipped CRC byte;
  - the first 40 bytes of `dirty.png`;
  - an unknown critical chunk `ZZZZ`;
  - IHDR not first;
  - a second IHDR;
  - IHDR of 12 bytes;
  - PLTE of 10 bytes;
  - an `acTL` chunk, refused as "animated PNG";
  - an IHDR claiming 20000×20000;
  - an IDAT of 5.5 MiB with a valid CRC, refused over 5 MiB;
  - an `eXIf` that is unreadable (garbage), which is refused;
  - an `eXIf` without an Orientation tag, which is accepted.
- **JPEG:**
  - `dirty.jpg` cut before EOI;
  - an unknown marker (`FF C8`);
  - SOF0 patched to `SOF3`, and separately to `SOF9`;
  - `cmyk.jpg` with its APP14 removed (4 components without APP14);
  - `dirty.jpg` with component IDs patched to `R`/`G`/`B`;
  - a second SOF;
  - a SOF height of 0;
  - a segment length of 1;
  - a non-`FF` byte where a marker is expected;
  - `FF FF` fill bytes before a marker, which are accepted and not copied;
  - a DQT whose length is one byte too long.
- **WebP:**
  - a RIFF size one too large;
  - a chunk size past the end;
  - `ALPH` next to `VP8L`;
  - two `VP8 ` chunks;
  - a VP8X with the animation flag and no `ANIM`;
  - a VP8X canvas that differs from the frame.
- **Other files:**
  - a sparse 21 MiB file (`truncate`);
  - SVG text in `shot.png`;
  - `GIF89a` bytes in `x.png`;
  - an empty file.

The test files:

- **`orchestrator/test_image_strip.py`**, per dirty fixture and in this order:
  - (a) the **input** carries every part listed in the table, found by
    `image_testwalk` (not `image_strip`), and contains `fixture-`;
  - (b) the **output** has only keep-list parts, and contains none of
    `fixture-`, `Exif`, `<x:xmpmeta`, `ICC_PROFILE`, `Photoshop` or
    `TRAILER`;
  - (c) the image data (PNG `IHDR`/`PLTE`/`tRNS`/`IDAT`; JPEG
    DQT/SOF/DHT/DRI/SOS and scan data; WebP `VP8 `/`VP8L`/`ALPH`) is
    byte-identical between input and output;
  - (d) the structure is sound: PNG CRCs valid, RIFF size equal to the length
    minus 8, JPEG begins with SOI plus the canonical JFIF and ends with EOI,
    WebP output in the form the table gives;
  - (e) the dimensions are 24×16.

  It also holds the refusal and keep paths of the built cases above.
- **`orchestrator/test_image_robust.py`** has two cases, both calling
  `prepare` in-process under a `signal.alarm(120)` guard, so a hang fails the
  test instead of stalling the run (all three places are Linux):
  - every fixture cut at every length from 0 to its full size;
  - for every fixture, 200 single-byte flips at positions and values drawn
    from `random.Random(243)`.

  Every result must be either output that `image_testwalk` accepts as clean
  and well-formed, or a `Refused`. Any other exception fails the test and
  names the fixture, the length or the flip. One CLI case runs a truncated
  file through `image_prep.py` and asserts exit 2, stderr starting with
  `image_prep:`, and no `Traceback` in it.
- **`orchestrator/test_image_fixtures.py`**: the sha256 of every fixture
  matches `orchestrator/testdata/SHA256SUMS`, and every image file in that
  directory is listed.
- **`orchestrator/test_image_prep.py`** runs the CLI as `[sys.executable,
  image_prep.py, src, outdir]`:
  - `dirty.jpg` exits 0, prints `<outdir>/image.jpg`, and that file passes
    (b).
  - `rotated.jpg` and `rotated.png` exit 2 with `orientation 6`.
  - The 2560 px refusal names the size, `2560`, `fullPage`, `scale: "css"`
    and `figsize`.
  - Every other built refusal exits 2 with `image_prep:` and its reason on
    stderr, and `outdir` stays empty.
- **`orchestrator/test_ping_image.py`** uses a fake `HOME` with
  `.local/bin/buzz` (`ping.sh` calls it by path), a fake `sops` on `PATH`,
  and the real `image_prep.py` with `dirty.png`. It does not prove the real
  CLI (gate 3). It pins:
  - the argv: `--channel <cid> --content <caption> --file <path> --mention
    <npub>`, with no `-` after `--content`;
  - that the temp directory is gone after the send;
  - that nothing is sent and `sops` is never called when the helper refuses
    (`rotated.png`, exit 10);
  - that a missing caption gives exit 9;
  - that a human IDENT is still refused with `--image` before the helper runs;
  - that the stderr for exits 9 and 10 is English.
- **`agents/test_notify.py`, `chat/test_imeta.py` and the listener source
  pin:** see "Notification".
- **`jobs/test_prune_media.py`:** a fake `ssh`, the prune followed by a size
  under (rc 0) and over (rc 1, size and limit printed, in English)
  `MEDIA_MAX_BYTES`.

## Risks

- **Dedup and age.** If the relay skips re-storing a blob it already has, an
  image re-sent on day 29 can be pruned a day later. Accepted (decision 4
  above): the follow-up shows "expired", which is true and visible.
- **Images are unseen until the follow-up.** The push says `🖼 caption` and the
  tap opens a thread without the picture. Accepted for the gap between the two
  changes.
- **The relay's metadata check is a black box.** It may refuse something the
  keep-lists keep. Gate 3 has a fixed fallback per format, so the host session
  does not have to make a design decision there.
- **No resize.** An image over 2560 px is refused, not shrunk. Agents make
  their own screenshots and charts, so the refusal message and the doc name
  the common traps (a Playwright `fullPage` screenshot, `deviceScaleFactor: 2`)
  and the fixes (clip or viewport ≤ 2560, `scale: "css"`, matplotlib
  `figsize × dpi` ≤ 2560). On exit 10 the agent crops, or sends a text ping
  instead.
- **Colour edge cases are refused, not guessed.** Adobe APP14, CMYK and
  RGB-coded JPEGs (component IDs `R`/`G`/`B`) are refused with "re-save as
  PNG", because dropping or inserting a colour marker would silently change
  the colours.
- **Colour profiles are dropped.** `iCCP`/APP2 ICC/`ICCP` go, so a wide-gamut
  image is shown as sRGB. For screenshots and charts that is no difference.
