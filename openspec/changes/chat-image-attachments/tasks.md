# Tasks

Part 1 of three after the split (proposal). Queued behind the other open work
(Mark, 2026-11-02): not built before `agent-image-to-chat` is archived.

## 1. Gates
- [x] **buzz media.** Passed 2026-11-24 (design.md, "Gate results"); the
      relay carries media, and the split decides the image goes through it.
- [x] **Vision through Read.** Passed 2026-11-24 for sonnet, haiku and opus.
- [ ] **Gate A: the chat's CLI sends a file** (host, before the build).
      Proof: the command, the CLI version and the event's `imeta` tag,
      recorded in design.md under Gates. If the CLI has no `--file`, stop:
      a `BUZZ_REF` bump is its own change.

## 2. Server
- [ ] `chat/server.py` branches `/api/upload` off `do_POST` before the 16 KiB
      read: gate first (session and CSRF), then `chat/upload.py`. Proof:
      `chat/test_upload.py` shows no body is read without a session, without
      a CSRF token, without a Content-Length, with a chunked body, and with a
      length over 5 MiB.
- [ ] `chat/upload.py`: magic bytes, the shared helper's prepare and strip,
      the caption required (≤ 2 000 characters), then `buzz messages send
      --content - --file <tmp>` signed as the chat's identity; the temp file
      removed on every exit. Proof: `chat/test_upload.py` covers an
      `image/png` header over JPEG bytes, an SVG, a GIF, a JPEG with EXIF and
      COM whose stored bytes have neither (asserted on the bytes handed to
      buzz, against the committed fixtures of `orchestrator/testdata`), a
      rotated-orientation JPEG refused with the helper's reason, a missing
      caption, a relay refusal answered 502 with its reason, and the temp file
      gone after success and after a failure.
- [ ] The helper is loaded by file path from `../orchestrator/` in the repo
      and from `/app/` in the image; `chat/Dockerfile` copies `image_prep.py`,
      `image_strip.py`, `image_exif.py` and `image_selfcheck.py`. Proof: a
      test that compares the Dockerfile's copy list with the helper modules'
      own imports, and fails when one is missing.
- [ ] The chat image pin moves one minor version in
      `deploy/docker-compose.yml`. Proof: `scripts/pin_check.py` green.

## 3. Seam
- [ ] One test runs `chat/upload.py` up to the buzz call and parses the
      resulting event shape with `chat/imeta.py` against
      `chat/testdata/imeta-event.json`, so the sender and the one parser
      agree. Proof: `chat/test_upload_seam.py`, shown to fail when the
      attached file's type and the tag's `m` disagree.

## 4. Live
- [ ] After the deploy: `chat/e2e/api.sh` uploads a prepared PNG to a test
      channel and finds one message from mark with an `imeta` tag; an SVG is
      refused with its reason. Proof: the run's output on the issue.

## 5. Docs (CI fails on code without docs)
- [ ] `docs/how-to/ping-from-a-session.md`: the chat HTTP API list gains
      `/api/upload`, with its query parameters, limits and status codes.
- [ ] `docs/how-to/send-an-image.md`: a section that the chat sends images by
      the same road, with the same limits and refusals.
- [ ] `chat/e2e/README.md`: what the upload step in `api.sh` needs.
- [ ] `docs/reference/roadmap.yml` if finishing this changes what "done"
      means.
