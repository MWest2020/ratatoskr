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
  ├─ image_prep.py  (uv, Pillow)
  │    magic bytes → decode → re-encode from raw pixels → ≤5 MiB
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

### Preparing the image happens on agent-lxc, with Pillow

`orchestrator/image_prep.py` is a uv script (`# /// script`, `pillow>=11,<12`,
the `push-notify.py` pattern). The chat image stays stdlib-only, as its
Dockerfile says it should. Steps, each refusal on stderr with exit 2 and a
reason:

1. The file exists and is ≤ 20 MiB.
2. The magic bytes are PNG, JPEG or WebP. The extension is not consulted, and
   SVG, GIF, HEIC and everything else are refused by name.
3. `Image.open(f, formats=["PNG","JPEG","WEBP"])`, with
   `MAX_IMAGE_PIXELS = 40_000_000` and `DecompressionBombWarning` raised as an
   error.
4. `ImageOps.exif_transpose`, so the orientation survives the strip. Then the
   first frame only.
5. Fit inside 2560×2560 (`thumbnail`, LANCZOS).
6. **Re-encode from raw pixels:** `Image.frombytes(mode, size, tobytes())`, so
   no `info` dict, EXIF, XMP, ICC profile or text chunk is carried over. Save in
   the source format: PNG `optimize`, JPEG `quality=88`, WebP `quality=88`.
   `P`, `LA` and `CMYK` are converted to `RGBA` or `RGB` first.
7. Output ≤ 5 MiB, or refuse with the size.
8. Print the output path. `ping.sh` puts the file in a `mktemp -d` that a
   `trap` removes.

The relay refuses metadata on its own (422, measured), so a file that slips
past the helper is stopped there too. That is defence in depth, not the plan.

Rejected: **stdlib segment stripping**. It is hand-written parsing of three
container formats, and the #223 architect called out exactly this as the part
that looks right while it keeps an APP1. Re-encoding from pixels has nothing to
forget. Also rejected: **stripping in the chat**. That would mean either a
dependency in a deliberately stdlib-only image, or the same hand parser.

### The helper is `ping.sh`, extended

```
IDENT=architect CHAN=architectuur orchestrator/ping.sh --image chart.png 'p95 latency, last 7 days'
```

`--image <path>` has to be the first argument. A caption is required, because
the notification and the `alt` text need one. Everything else in `ping.sh`
stays as it is: IDENT lookup, the human identity refused, inactive identities
refused, `#general` hub-only for sessions, and the nsec from SOPS. The only
other difference is on the `buzz messages send` line: the image branch sends
`--content "$MSG" --file "$OUT"`, exactly the form gate 1.1 measured. It does
not keep the text path's `--content -` (stdin): stdin together with `--file`
was never measured, so it is not used. The text-only branch is unchanged. Exit
codes are new for an image refusal (10) and a missing caption (9), and the
reason is on stderr.

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
2. **Pillow offline fails red, and says why.** If `uv` cannot resolve Pillow,
   `test_image_prep.py` fails, never skips. A guard test classifies the
   failure in its message: the resolve step failed (index unreachable, offline
   cache empty: "no network") versus Pillow resolved and the script or its
   assertions failed ("broken code"). Both are red; the message tells the
   reader which one to fix. The change proves it on agent-lxc and in CI.
   Rejected: *vendoring the wheels* (a binary blob in git for a dependency uv
   resolves anyway); *running the strip test on the host only* (that is a
   skipped layer, and a skip does not count); *a skip with a warning*.
3. **One parser, one fixture.** Caption and `imeta` parsing exists once, as a
   shared stdlib-only helper, tested against `chat/testdata/imeta-event.json`.
   The notification uses it here, and `agent-image-to-chat-read` reuses it for
   `images` and the cleaned content instead of writing a second parser. Its
   location is an open question in the proposal.
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

### Notification: text, with a marker

`agents/listener.py` is at 200 lines. The `notify.push` call in the listener
(line 162) passes `m.get("tags")` as a fourth argument (same line count), and
`notify._body` gets the tags through `_last` and `flush` (see above). When an
image `imeta` tag is present, the body becomes `🖼 <caption>`,
with the Markdown image line removed from the caption (see gate 1). Cooldown,
held-back messages and `+n` stay as they are. The push payload stays text (Web
Push payloads are about 4 KiB), and a tap opens `/#<channel>`.

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
  04:30, `Persistent=true` (a missed day should still run).
- **Why loud:** a failing timer is caught by `scripts/check_timers.py`, and it
  shows in Mark's digest as an impediment once it has failed for 12 hours. A
  size alarm that only writes a log line would be the silent failure that
  AGENTS.md forbids.
- **Expected volume:** 5 MiB is the ceiling and a screenshot after the 2560 px
  fit is typically 0.3–1.5 MiB. Twenty images a day for 30 days is about
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
3. **JPEG and WebP through the relay (live).** Upload one helper-prepared file
   of each format, through the real `ping.sh --image`, which also proves that
   `--content '<caption>' --file <path>` is accepted by the real CLI. The
   relay's metadata check must accept Pillow's JFIF APP0 and a plain
   `VP8 `/`VP8L` RIFF. If it refuses one, change the save options for that
   format.
4. **On the phone (live).** The `🖼 caption` notification shows and a tap opens
   the channel. Separately, record whether a `showNotification` with an `image`
   (a `data:` URL built by the SW) shows on Mark's Android. Record only; do not
   build it.

## Tests

- `orchestrator/test_image_prep.py` runs the real script through `uv run`.
  **It never skips.** If `uv` cannot resolve Pillow (offline cage), the test
  fails with the reason; a skipped layer does not count (AGENTS.md). A
  `conftest` guard or an explicit first test asserts that Pillow resolves, so
  a missing Pillow is one red test and not a green run of nothing. The host
  runs it in a verify step (task 1.3), where Pillow resolves, so the
  metadata-strip check has run at least once before deploy. Small committed
  fixtures are in `orchestrator/testdata/`: a PNG with `tEXt`+`eXIf`+`iCCP`, a
  JPEG with an Exif APP1 holding GPS and an orientation of 6, a WebP with an
  `EXIF` chunk, an SVG renamed to `.png`, a PNG header that claims 20000×20000,
  a truncated PNG, and a 21 MiB file. The assertions are on the **output
  bytes**: only `IHDR/PLTE/tRNS/IDAT/IEND` in the PNG, no APP1/APP2/COM in the
  JPEG, no `EXIF`/`XMP `/`ICCP` in the WebP, the rotation applied, each refusal
  with its reason, and the output ≤ 5 MiB and ≤ 2560 px.
- `orchestrator/test_ping_image.py`: fake `buzz`, `sops` and `uv` on `PATH`; it
  pins the argv `ping.sh` builds. It does not prove the real CLI (gate 3).
- `agents/test_notify.py`: an image message, built from
  `chat/testdata/imeta-event.json`, gives `🖼 caption` without the Markdown
  image line, and the cooldown behaviour is unchanged for image messages. The
  seam test calls `push` (held by the cooldown) and then `flush`, and asserts
  the delivered body is `🖼 caption`; a second case does the same for a plain
  text message to pin that nothing else changed.
- A test of the shared imeta/caption helper against the same fixture.
- The Pillow guard test (above) in `orchestrator/test_image_prep.py`, run on
  agent-lxc and in CI.
- `jobs/test_prune_media.py`: a fake `ssh`, prune then size under and over
  `MEDIA_MAX_BYTES`.

## Risks

- **Dedup and age.** If the relay skips re-storing a blob it already has, an
  image re-sent on day 29 can be pruned a day later. Accepted (decision 4
  above): the follow-up shows "expired", which is true and visible.
- **Images are unseen until the follow-up.** The push says `🖼 caption` and the
  tap opens a thread without the picture. Accepted for the gap between the two
  changes.
- **Pillow in the cage.** If `uv` cannot resolve it there, the build is red on
  the Pillow test, by design (decision 2 above), and the guard test says
  whether the cause is the network or the code.
