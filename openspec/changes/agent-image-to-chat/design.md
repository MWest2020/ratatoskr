# Design: agent → chat → phone, one image per message

## The path

```
agent-lxc                              relay VM (buzz-relay)                    phone
─────────                              ─────────────────────                    ─────
IDENT=x CHAN=y ping.sh --image p 'c'
  ├─ image_prep.py  (uv, Pillow)
  │    magic bytes → decode → re-encode from raw pixels → ≤5 MiB
  └─ buzz messages send --file  ──LAN──▶ relay :3000
                                          ├─ Blossom store (SeaweedFS, buzz-media)
                                          └─ signed event + imeta tag
                                                 ▲
                                    chat ──buzz-net──┘  messages get / media get
                                    (session-gated)
                                    GET /api/messages  → images[]       ◀──tailscale serve── PWA
                                    GET /api/media/<sha256> → bytes      ◀──────────────────  <img>
listener (agent-lxc) sees the event ─▶ notify.py "🖼 caption" ─▶ push-notify.py ─▶ FCM ─▶ notification
```

Every hop in this picture already exists and already carries traffic today.
Only `--file`, the `/api/media/` route and the `🖼` prefix are new.

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

**Not measured:** sending a message with `--file`. The auto-mode classifier
refused that probe because it writes to a channel, so the shape of the `imeta`
tag on the event is gate 1 below.

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

### The chat proxies, behind the session

The relay's media URL answers 401 without Blossom auth, and the phone cannot
sign Blossom requests. So the chat serves the image itself:
`GET /api/media/<sha256>` passes `auth_routes.gate(..., writes=False)` like
every other `/api/` read. It then runs `buzz media get <sha256> -o -` under the
chat's own key (the process identity, `mark`; `rotate-mark-identity` already
verified that `media get` works with it). The response:

- 400 unless the path is exactly 64 lowercase hex characters.
- 410 `{"error":"image expired (kept 30 days)"}` when buzz reports 404.
- 502 `{"error":"<buzz message, 200 chars>"}` on any other buzz failure or a
  timeout (25 s).
- 502 when the blob is over 5 MiB. It is read with a ceiling and is never
  buffered past it.
- 415 unless the first bytes are PNG (`89 50 4E 47 0D 0A 1A 0A`), JPEG
  (`FF D8 FF`) or WebP (`RIFF....WEBP`). Any blob can be fetched by hash, so
  this is what keeps an HTML or SVG blob, uploaded with raw `buzz` by anyone in
  the community, from being served as a document on the chat's origin.
- 200 with `Content-Type` taken from the magic bytes (never from the event or
  the extension), `X-Content-Type-Options: nosniff`,
  `Content-Security-Policy: default-src 'none'; sandbox`, `Cache-Control:
  no-store` and `Content-Disposition: inline`.

`no-store` is deliberate even though the content is addressed by hash. A 401
clears what the app keeps locally (webchat-pwa: "Een 401 wist de lokaal
bewaarde berichten"), and an HTTP cache would quietly keep the pictures after a
logout. The UI keeps its own in-memory cache instead, described below.

`buzzcli.buzz()` uses `text=True`, so the new `chat/media.py` calls
`subprocess.run` with bytes itself, with the same `BUZZ_BIN` and environment.

Rejected: **an unauthenticated route keyed by hash** (the hash as a
capability). It would be the first session-less read on an app whose docs call
the tailnet the door, not a second lock (`docs/naar-een-product.md`). Also
rejected: **having the browser talk to the relay**. The relay is not on the
phone's path, and the phone cannot do Blossom auth.

### `/api/messages` carries `images`, parsed from `imeta`

`read_routes.py` adds `"images": media.from_tags(m.get("tags"))` for each
message: a list of `{"sha256", "type", "dim"}`. The parser takes NIP-92 `imeta`
tags (`["imeta", "url …", "m …", "x …", "dim …", …]`). It uses `x` for the
hash, or the 64-hex basename of `url` when `x` is missing. It keeps only
`image/png`, `image/jpeg` and `image/webp`, and at most four entries. Anything
that does not parse is dropped and the message still renders. `content` is
cleaned of any URL that ends in `/media/<that hash>.<ext>`, in case buzz writes
the URL into the text as well (gate 1 decides whether it does). The phone could
not open that LAN URL anyway.

The exact tag shape comes from gate 1. The recorded event is committed as
`chat/testdata/imeta-event.json` and drives the parser test, so the format that
both sides share is pinned by one real sample rather than by two assumptions.

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
other difference is `--file "$OUT"` on the `buzz messages send` line. Exit
codes are new for an image refusal (10) and a missing caption (9), and the
reason is on stderr.

Rejected: **a separate `ratatoskr-send` CLI**. It would be a second post path,
and the identity rules would have to be kept equal in two places. That is how
an impersonation guard ends up missing from one of them.

### UI: one hook line, one new file

`chat/app.js` is at exactly 200 lines. Line 148 becomes

```js
for(const f of [window.decorateRow, window.decorateImage]) if(typeof f==="function") f(row, m, msgs);
```

The line count stays the same and nothing in app-reply.js changes. The new
`chat/app-image.js` defines `decorateImage(row, m)`:

- For each `m.images[i]` whose `sha256` matches `/^[0-9a-f]{64}$/`, it appends
  a `<button class="msgimg">` holding an `<img alt=caption>` under the bubble.
- The bytes come from `fetch("/api/media/"+sha)`, then a blob, then
  `URL.createObjectURL`. That is not the same as `<img src>`: `fetch` sees the
  status, so the UI can say *why* an image is missing ("image expired",
  "offline", "relay: …"). Status 401 goes to the existing logged-out flow.
- An in-memory `Map` (sha → object URL, LRU of 30, `revokeObjectURL` on
  eviction) stops `renderMessages`, which rebuilds the thread on every new
  message, from fetching every image again. The map dies with the page, and
  with it everything a 401 should clear.
- A tap opens a full-screen overlay (`.imgview`) with the same object URL,
  `touch-action: pinch-zoom`. A tap, Escape or Back closes it; the view pushes
  a history entry so Back on Android closes the view and not the app.
- Everything from a message enters the DOM through `el`/`add` (textContent),
  never `innerHTML`. `chat/e2e/xss.js` keeps guarding that.

Styles go in a new `chat/image.css`. `app.css` is at 174 lines, and the next
change should not have to make room. Both new files are registered in all four
places: `chat/statics.py` FILES, `chat/sw.js` SHELL and FRESH_ASSETS, and
`chat/index.html`. `CACHE` in `sw.js` goes to `v32` with a note.

The offline snapshot stores `images` along with the rest of each message.
Offline, `fetch` fails and the placeholder says "image not available offline".

### Notification: text, with a marker

`agents/listener.py` is at 200 lines. Line 164 passes `m.get("tags")` as a
fourth argument to `notify.push` (same line count), and `notify._body` gets
the tags. When an image `imeta` tag is present, the body becomes `🖼 <caption>`,
with any media URL removed from the caption. Cooldown, held-back messages and
`+n` stay as they are. The push payload stays text (Web Push payloads are about
4 KiB), and a tap opens `/#<channel>`, where the image is inline.

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
- **After the prune:** the message text stays. The chat answers 410, and the
  thread shows "image expired (kept 30 days)".

Rejected:
- **Never prune.** #223's trap: the store is append-only by construction.
- **A bucket lifecycle rule in SeaweedFS.** It is invisible in git, support
  through the S3 API is unverified, and it applies to the whole bucket.
- **Blossom DELETE signed by the uploader.** The CLI has no delete, and the
  uploader's key lives on another host than the store.
- **A cap per volume with oldest-first eviction.** That needs an inventory and
  an ordering, which is more code for the same outcome. An age is easier to
  state to Mark ("a picture lives 30 days").

## Gates (before or during the build)

1. **imeta shape (host, before the build).** The coordinating session on
   agent-lxc sends one image message with `buzz messages send --file` into
   `#statistics`, which never pushes (`notify.SILENT`), and reads it back with
   `messages get`. It records whether the content gains the URL, commits the
   event as `chat/testdata/imeta-event.json`, and then deletes the message. If
   there is no `imeta` tag, or no `x` or `url` in it, amend this design before
   building.
2. **Bucket inventory (host, before enabling the timer).** Run `docker compose
   run --rm media-prune lsf dst:buzz-media` and record the key layout and every
   key that is not an image. If keys have no extension, or something other than
   chat media lives there (custom emoji, avatars, persona packs), the
   `--include` filter is not safe. The timer then stays disabled and a
   `waiting-on-mark` issue says so. Default in that case: prune by a list of
   hashes collected from the `imeta` tags of messages older than 30 days.
3. **After a prune (live).** `buzz media get` on a deleted hash returns 404,
   not a 500 from a dangling row in the relay database. Otherwise the chat maps
   the error to "relay error", and the UI shows that text instead of "expired".
4. **JPEG and WebP through the relay (live).** Upload one helper-prepared file
   of each format. The relay's metadata check must accept Pillow's JFIF APP0
   and a plain `VP8 `/`VP8L` RIFF. If it refuses one, change the save options
   for that format.
5. **On the phone (live).** In the installed PWA over `tailscale serve`, the
   image shows inline and opens full size, and Back closes the view without
   leaving the app. Separately, record whether a `showNotification` with an
   `image` (a `data:` URL built by the SW) shows on Mark's Android. Record only;
   do not build it.

## Tests

- `orchestrator/test_image_prep.py` runs the real script through `uv run`
  (skipped, with a stated reason, when `uv` cannot resolve Pillow offline).
  Small committed fixtures are in `orchestrator/testdata/`: a PNG with
  `tEXt`+`eXIf`+`iCCP`, a JPEG with an Exif APP1 holding GPS and an
  orientation of 6, a WebP with an `EXIF` chunk, an SVG renamed to `.png`, a
  PNG header that claims 20000×20000, a truncated PNG, and a 21 MiB file. The
  assertions are on the **output bytes**: only `IHDR/PLTE/tRNS/IDAT/IEND` in
  the PNG, no APP1/APP2/COM in the JPEG, no `EXIF`/`XMP `/`ICCP` in the WebP,
  the rotation applied, each refusal with its reason, and the output ≤ 5 MiB
  and ≤ 2560 px.
- `chat/test_media.py`: no session → 401; a bad hash → 400; buzz 404 → 410; a
  buzz error → 502 with the reason; a blob over 5 MiB → 502; HTML or SVG bytes
  → 415; PNG, JPEG and WebP → 200 with the right type and all four headers; a
  HEAD request → headers only. `from_tags` against
  `chat/testdata/imeta-event.json`, against a tag without `x`, and against
  junk. Content cleaning.
- `agents/test_notify.py`: an image message gives `🖼 caption` without the URL,
  and the cooldown behaviour is unchanged for image messages.
- **The seam** (`chat/test_media_seam.py`): the bytes `image_prep.py` writes
  for the PNG fixture go into a fake `buzz` binary (`BUZZ_BIN` pointing at a
  script that prints them for `media get`). The real route serves them with
  `image/png`, and `from_tags` on the recorded event yields that sha. Break one
  side (the magic sniff, or the `x` field name) and the test fails. Check that
  by breaking it once.
- `chat/e2e/image.js` (deploy layer, Playwright): open `#statistics` with the
  gate-1 message, the `<img>` has a `naturalWidth` above 0, a tap opens
  `.imgview`, Escape closes it, and a forced 410 shows "image expired".
  `xss.js` and `smoke.js` still pass.

## Risks

- **Any community member can upload any blob, and the route serves by hash.**
  Mitigated by the magic-byte allowlist, a fixed Content-Type, `nosniff`, and a
  sandbox CSP on the response. The route does not check that the hash appears
  in a message. Every session holder is Mark, and the relay already decides who
  may upload.
- **Dedup and age.** If the relay skips re-storing a blob it already has, an
  image re-sent on day 29 can be pruned a day later. Accepted: the thread says
  "expired", which is true and visible.
- **`renderMessages` rebuilds on each new message.** Without the in-memory map,
  every image would be fetched again each time. The map is the mitigation, and
  the e2e counts `/api/media/` requests on a re-render.
- **Two images on one hook line.** If a third decorator turns up, the array on
  line 148 grows. That is fine up to the 200-line limit, and after that a
  registry is the honest fix.
