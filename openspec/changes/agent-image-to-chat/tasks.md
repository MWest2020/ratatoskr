# Tasks

One build: section 2. Sections 1 and 3 need the relay, SOPS or the phone,
which the build cage does not have, so a host session on agent-lxc runs them.
The build may start once 1.1 is recorded. 1.2 only blocks 3.3.

## 1. Gates on the host (not in the cage)
- [x] **Measured 2026-11-13.** An agent key can upload, the relay refuses
      metadata (422), `media get` is byte-identical, the media URL is 401
      without auth, and 5 MiB is accepted. Recorded in design.md, "Measured".
- [ ] 1.1 **imeta shape.** Send one image message with
      `buzz messages send --file` to `#statistics` as an identity that is a
      member there. Read it back with `messages get`, then delete it. Commit
      the event as `chat/testdata/imeta-event.json`. Note in design.md whether
      `content` gains the URL. Proof: the file is committed and design.md
      states the tag fields. If there is no `imeta` with `x` or `url`, amend
      design.md first.
- [ ] 1.2 **Bucket inventory.** Run
      `ssh buzz-relay 'cd /opt/buzz-relay && sudo docker compose run --rm seaweedfs-init lsf dst:buzz-media'`
      (or `media-prune` once it is deployed). Record the key layout and any
      key that is not an image in design.md. Proof: the listing summary is in
      design.md. If the `--include` filter is unsafe, open a `waiting-on-mark`
      issue with the hash-list default from design.md.

## 2. Build (one run)
- [ ] 2.1 `orchestrator/image_prep.py` (uv script, Pillow) as in design.md,
      plus fixtures in `orchestrator/testdata/` and
      `orchestrator/test_image_prep.py`. Proof: the test passes, and its
      assertions are on the output bytes.
- [ ] 2.2 `orchestrator/ping.sh --image <path> 'caption'`: prep into a
      `mktemp -d` with a `trap` cleanup, then `--file` on the send. Exit 9 for
      a missing caption, 10 for a refused image. Every existing IDENT and
      channel rule is untouched. Proof: a shell test in
      `orchestrator/test_ping_image.py` with a fake `buzz`, `sops` and `uv`
      on `PATH`. It covers the argv gaining `--file`, the temp directory being
      gone after the send, no send when prep fails, and a human IDENT still
      refused with `--image`.
- [ ] 2.3 `chat/media.py`: `from_tags`, `clean_content`, and the
      `/api/media/<sha256>` route with the status codes and headers in
      design.md. `chat/read_routes.py` dispatches to it and adds `images`.
      Proof: `chat/test_media.py`.
- [ ] 2.4 `chat/app-image.js` and `chat/image.css`; the hook line in
      `chat/app.js` (still 200 lines); registered in `statics.py`, `sw.js`
      SHELL and FRESH_ASSETS, and `index.html`; `CACHE` set to `v32`. Proof:
      `bash verify.sh` green (line limit included), and `chat/test_server.py`
      serves both new files.
- [ ] 2.5 `agents/notify.py` `🖼` body, with `listener.py` line 164 passing
      the tags (still 200 lines). Proof: new cases in `agents/test_notify.py`.
- [ ] 2.6 The seam: `chat/test_media_seam.py` as in design.md. Proof: it is
      green, and it fails once when the magic sniff or the `x` field is broken
      on purpose. Say in the PR that this was checked.
- [ ] 2.7 Retention: the `media-prune` service (profile `maintenance`, rclone
      1.71) in `deploy/docker-compose.yml`, `jobs/prune-media.sh`, and
      `jobs/systemd/ratatoskr-media-prune.{service,timer}`. Proof: `bash -n`
      on the script, `pin_check.py` green, and `jobs/test_prune_media.py` with
      a fake `ssh` covering a prune followed by a size under and over
      `MEDIA_MAX_BYTES` (rc 0 and rc 1, the reason printed).
- [ ] 2.8 Chat image pin `0.17.0` → `0.18.0` in `deploy/docker-compose.yml`.
- [ ] 2.9 `chat/e2e/image.js` and its section in `chat/e2e/README.md`.
- [ ] 2.10 Docs, since CI fails on code without docs:
      `docs/how-to/send-an-image.md` (new: the command, limits, types,
      caption, exit codes, the 30-day retention, what Mark sees, and
      failures); `docs/how-to/ping-from-a-session.md` (`--image`, plus
      `/api/media/` in the chat API list); `docs/how-to/troubleshooting.md`
      (a "no image" section: 410 versus 502, and the prune timer).

## 3. Live (host session, after merge)
- [ ] 3.1 Tag `chat-v0.18.0`, copy the compose file to `/opt/buzz-relay`, run
      `docker compose up -d chat`, then `chat/e2e/after-deploy.sh` and
      `node chat/e2e/image.js`. All layers must be green; a skipped layer does
      not count.
- [ ] 3.2 Gate 4: one prepared PNG, JPEG and WebP each through `ping.sh
      --image` to `#statistics`. Record in design.md.
- [ ] 3.3 Install and enable the prune units (`check_units.py` and
      `check_timers.py` green). Gate 3: run it once and record the outcome of
      `media get` on a deleted hash.
- [ ] 3.4 Gate 5 on Mark's phone: a real `ping.sh --image` to a project
      channel. The notification reads `🖼 caption`, a tap opens the thread,
      the image is inline, full size opens on tap, and Back closes it. Record
      the notification-image probe in design.md.
- [ ] 3.5 Update `docs/reference/roadmap.yml` if this changes what "done"
      means for the chat. Archive this change.
