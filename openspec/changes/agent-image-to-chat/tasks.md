# Tasks

Scope after the split (ratatoskr#260): sender (A), notification and retention
(C). The read path is the follow-up `agent-image-to-chat-read` and is not built
here. One build: section 2. Sections 1 and 3 need the relay, SOPS or the phone,
which the build cage does not have, so a host session on agent-lxc runs them.
The build may start once 1.1 is recorded (it is). Gate 0 is not a gate of this
change.

## 1. Gates on the host (not in the cage)
- [x] **Measured 2026-11-13.** An agent key can upload, the relay refuses
      metadata (422), `media get` is byte-identical, the media URL is 401
      without auth, and 5 MiB is accepted. Recorded in design.md, "Measured".
- [x] 1.1 **imeta shape.** Recorded 2026-11-24 (design.md, "Measured on
      2026-11-24"): `imeta` has `url`, `m`, `x`, `size`, `dim`, `blurhash`,
      `thumb`; `content` gains a `![image](<url>)` line. The event is committed
      as `chat/testdata/imeta-event.json`. Proof: the file is committed and
      design.md states the tag fields.
- [ ] 1.2 **Bucket inventory.** Run
      `ssh buzz-relay 'cd /opt/buzz-relay && sudo docker compose run --rm seaweedfs-init lsf dst:buzz-media'`
      (or `media-prune` once it is deployed). Record the key layout and any
      key that is not an image in design.md. Proof: the listing summary is in
      design.md. If the `--include` filter is unsafe, open a `waiting-on-mark`
      issue with the hash-list default from design.md. Only blocks 3.3.
- [ ] 1.3 **Host verify step for the metadata strip.** On agent-lxc, where `uv`
      resolves Pillow, run `uv run pytest orchestrator/test_image_prep.py -rs`
      as a step of the host's pre-deploy check, wired into `verify.sh` (the
      local gate; AGENTS.md) so it runs where Pillow resolves. Proof: the
      output shows every test passed, **0 skipped**; a skipped or missing
      Pillow test makes the deploy not green (AGENTS.md: skipping does not
      count as passing).

## 2. Build (one run)
- [ ] 2.1 `orchestrator/image_prep.py` (uv script, Pillow) as in design.md,
      plus fixtures in `orchestrator/testdata/` and
      `orchestrator/test_image_prep.py`. The test **never skips**: when `uv`
      cannot resolve Pillow it fails with the reason, through a guard test
      that asserts Pillow resolves. Proof: the test passes where Pillow
      resolves, a deliberately unresolvable Pillow (for example `UV_OFFLINE=1`
      with an empty cache) turns it red, not skipped, and its assertions are on
      the output bytes. Say in the PR that the red case was checked.
- [ ] 2.2 `orchestrator/ping.sh --image <path> 'caption'`: prep into a
      `mktemp -d` with a `trap` cleanup, then `--file` on the send. The image
      branch passes the caption as `--content "$MSG" --file "$OUT"`, the form
      gate 1.1 measured. It must **not** use `--content -` (stdin) together
      with `--file`; that combination was never measured. The text-only branch
      keeps `--content -` as it is today. Exit 9 for a missing caption, 10 for
      a refused image. Every existing IDENT and channel rule is untouched.
      Proof: a shell test in `orchestrator/test_ping_image.py` with a fake
      `buzz`, `sops` and `uv` on `PATH`. It covers the argv gaining `--file`
      with the caption as the `--content` value and no `-` anywhere after
      `--content`, the temp directory being gone after the send, no send when
      prep fails, and a human IDENT still refused with `--image`. **This fake
      does not prove that the real CLI accepts the combination**: it only
      pins which argv `ping.sh` builds. The real CLI is proved by the live
      check in 3.2.
- [ ] 2.3 `agents/notify.py` `🖼` body, with `listener.py` line 164 passing
      the tags (still 200 lines). The caption has the whole
      `\n![image](…/media/<hash>.<ext>)` line removed. Proof: new cases in
      `agents/test_notify.py` built from `chat/testdata/imeta-event.json`, and
      cooldown cases for image messages unchanged.
- [ ] 2.4 Retention: the `media-prune` service (profile `maintenance`, rclone
      1.71) in `deploy/docker-compose.yml`, `jobs/prune-media.sh`, and
      `jobs/systemd/ratatoskr-media-prune.{service,timer}`. Proof: `bash -n`
      on the script, `pin_check.py` green, and `jobs/test_prune_media.py` with
      a fake `ssh` covering a prune followed by a size under and over
      `MEDIA_MAX_BYTES` (rc 0 and rc 1, the reason printed).
- [ ] 2.5 Docs, since CI fails on code without docs. Grep under `docs/` found
      these that describe this behaviour:
      `docs/how-to/send-an-image.md` (new: the command, limits, types,
      caption, exit codes, the 30-day retention, the `🖼 caption` push, that
      the thread does not show the picture until `agent-image-to-chat-read` is
      built, and failures);
      `docs/how-to/ping-from-a-session.md` (`--image`);
      `docs/how-to/troubleshooting.md` (a "no image" section: the helper's
      exit codes 9 and 10, and the prune timer). Proof: the three files
      contain `--image`, and `bash verify.sh` is green.

## 3. Live (host session, after merge)
- [ ] 3.1 Gate 3: one prepared PNG, JPEG and WebP each through `ping.sh
      --image` to `#statistics`. Record in design.md. This is the live check
      for the argv `ping.sh` builds (`--content '<caption>' --file <path>`,
      the form gate 1.1 measured): each send must return `accepted`, and
      `messages get` must show the `imeta` tag and the caption, then delete
      the messages. It is the only proof that the real CLI takes this
      combination; 2.2's fake `buzz` does not.
- [ ] 3.2 Run the 1.3 host verify step once more on the merged tree. Proof:
      0 skipped.
- [ ] 3.3 Install and enable the prune units (`check_units.py` and
      `check_timers.py` green) once 1.2 is recorded, and run the job once.
      Proof: the timer's journal shows the prune and a size under
      `MEDIA_MAX_BYTES`.
- [ ] 3.4 Gate 4 on Mark's phone: a real `ping.sh --image` to a project
      channel. The notification reads `🖼 caption` and a tap opens the
      channel. Record the notification-image probe in design.md.
- [ ] 3.5 Update `docs/reference/roadmap.yml` if this changes what "done"
      means for the chat. Archive this change.

## 4. Handover
- [ ] 4.1 Propose `agent-image-to-chat-read` from design.md, "Handed to
      `agent-image-to-chat-read`": Gate 0 first, with the exact `buzz media
      get` invocation and stdout flag; the `_send` headers extension with its
      two-sided test. Proof: the change exists on main and its design.md
      records Gate 0 before any task of its build.
