# Tasks

Scope after the split (ratatoskr#260): sender (A), notification and retention
(C). The read path is the follow-up `agent-image-to-chat-read` and is not built
here. The build is three separate runs, A, B and C (section 2), because the
single run hit 161 turns and $14.17 and stopped after 2.1 and 2.2
(ratatoskr#243, builder FAIL of 2026-11-26). A run builds only its own tasks
and nothing of the others. Sections 1 and 3 need the relay, SOPS, systemd on
agent-lxc or the phone, which the build cage does not have, so a host session
on agent-lxc runs them. The build may start once 1.1 and 1.3 are recorded
(both are). Gate 0 is not a gate of this change.

**Exit condition of every run:** `uv run --with pyyaml bash verify.sh` (the CI
command) is green, all of it, in the cage and in CI, with no exception and no
skip, plus the run's own `done_when` below. Nothing a run adds needs the
network, Pillow, `uv` or the host (design.md, fourth FAIL, gap 4).

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
- [x] 1.3 **Image fixtures.** Committed 2026-11-26 in the amend after the
      fourth architect FAIL and extended after the review of #267: eleven
      files in `orchestrator/testdata/` (seven dirty, two rotated, one CMYK,
      one animated), `SHA256SUMS`, and their host-only generator
      `orchestrator/testdata/make_image_fixtures.py`, pinned to
      `pillow==13.0.0` (design.md, "Tests", fixture table). Proof: the files
      are committed and `sha256sum -c SHA256SUMS` passes; Pillow 13 on
      agent-lxc reads the Exif (with GPS), XMP and ICC data of every dirty
      fixture; a throwaway keep-list prototype gave outputs with pixels
      identical to the inputs, `dirty-restart.jpg` included. The build does
      not run the generator and does not need Pillow.

## 2. Build (three runs: A, B, C)

Built 2026-11-26 as one PR, `build/agent-image-to-chat`, on top of the builder
branch below: run A checked and tightened, runs B and C added. Each run's
`done_when` holds; the boxes below are ticked on that evidence.

### Run A: the stripper helper and `ping.sh --image` (tasks 2.1, 2.2)
Run A **starts from main** and builds to the #267 design (bounded parsing,
exact lengths, APNG and RGB-coded JPEG refusals, the restart-marker fixture,
the truncation and flip sweep), as the tasks below say. It reuses no earlier
branch, including
`habitat/builder/agent-image-to-chat-20261126-091423-30416`, unless the task
description names that branch's **commit SHA** (pinned) **and** the passing
tests it brings (by name, run in the cage). Without both, nothing of it is
taken over (architect FAIL 5, finding 1).
**done_when:** both commands of 2.1's proof and the test of 2.2 pass, every new
file is within its line budget, and `verify.sh` is green. Run A does not touch
`agents/`, `chat/`, `jobs/`, `deploy/` or `docs/`.

- [x] 2.1 The helper, stdlib only, SPDX headers, in the files and line budgets
      of design.md "Files and line budget": `orchestrator/image_strip.py`,
      `orchestrator/image_exif.py`, `orchestrator/image_prep.py` (with
      `prepare(data)` and `Refused`), and the test walker
      `orchestrator/image_testwalk.py`. Build it exactly as design.md
      "Preparing the image" says: the eight steps in order, the input read as
      `read(LIMIT + 1)`, the bounded-parsing rules (forward progress, JPEG
      length < 2 and non-`FF` refused, fill bytes skipped, the `cannot parse
      <fmt>` catch-all), the dimension rules, duplicates refused, exact
      lengths of kept parts, the three keep-lists with their refusals (APNG,
      animated WebP, APP14, RGB-coded JPEG, other SOFn), the orientation rule,
      the self-check, and every refusal as `image_prep: <reason>` on stderr
      with exit 2 and nothing written. The 2560 px message names the traps
      and fixes. Tests: `test_image_strip.py`, `test_image_prep.py`,
      `test_image_robust.py` and `test_image_fixtures.py`, as design.md
      "Tests" lists them. They are `unittest.TestCase` only (no pytest, no
      conftest, no bare `def test_*`, no `skipTest`), driven by the committed
      fixtures and the cases built in the tests. For every dirty fixture the
      test first proves the **input** dirty with `image_testwalk` and the
      `fixture-` sentinel, then the **output** clean, then the image data
      byte-identical. Proof: `cd orchestrator && python3 -m unittest discover
      -p 'test_image_*.py' -v` lists every case as `ok`, including every
      built refusal design.md names and the truncation and flip sweep (no
      traceback, no alarm); `grep -n skip orchestrator/test_image_*.py` finds
      nothing; `python3 scripts/line_limit.py` is green, with every new file
      within its budget.
- [x] 2.2 `orchestrator/ping.sh --image <path> 'caption'`, in the order
      design.md gives: argument branch (exit 9 without a caption), the
      unchanged IDENT and channel checks, then the helper into a `mktemp -d`
      with a `trap` cleanup **before** `sops -d` (exit 10 on refusal, through
      `|| { …; exit 10; }` because of `set -e`), then the send with
      `--content "$MSG" --file "$OUT" --mention "$NPUB"`. Never `--content -`
      together with `--file`. The text-only branch is unchanged. Proof:
      `orchestrator/test_ping_image.py` with a fake `HOME` holding
      `.local/bin/buzz` and a fake `sops` on `PATH`. It covers the exact argv,
      the temp directory gone after the send, no send and no `sops` call when
      the helper refuses, exit 9, a human IDENT still refused before the helper
      runs, and English stderr for exits 9 and 10. **The fake does not prove
      the real CLI**; 3.1 does.
### Run B: image push wiring and `chat/imeta.py` (tasks 2.4a, 2.3)
Run B builds on main with run A merged. It includes the listener split, so
that `agents/listener.py` stays at or under 200 lines. Build 2.4a first: 2.3
loads it. **done_when:** `chat/test_imeta.py` and `agents/test_notify.py` pass,
`orchestrator/test_push_chain.py` and `orchestrator/test_push_send.py` are
unchanged and green, `wc -l agents/listener.py` is at most 200 (199 as
designed), and `verify.sh` is green. Run B does not touch the helper,
`ping.sh`, `jobs/`, `deploy/` or `docs/`. (2.4a is listed after 2.3 below for
numbering; it is built first.)

- [x] 2.3 Notification, without growing `agents/listener.py`: lines 161-162
      become the single line `notify.on_message(cname, writer, m, ME_NAME)`
      (the file goes to 199 lines). **In the same edit**, the comment at
      `agents/listener.py:159` is rewritten to name `notify.on_message`
      instead of `notify.should_notify` (`(what does not notify:
      notify.on_message)`), so no stale name stays behind. In `agents/notify.py`:
      `on_message(cname, author, event, me)`, `push(cname, author, content,
      tags=None)`, `held = (author, content, tags)` inside the unchanged
      `(t, missed, held)`, `flush` unpacking the triple, and `_body(content,
      missed, tags)` giving `🖼 <clean caption>` (or `🖼 image`) when
      `imeta.from_tags(tags)` is non-empty. This touches the **Web Push**
      silent chain. Proof: in `agents/test_notify.py` with `subprocess.run`
      patched, `on_message(fixture event)` gives the `--body` design.md states.
      The seam case (held inside the cooldown, then `flush`) gives the same
      body, and it **fails** when `held` is cut back to `(author, content)`;
      say in the PR that this was checked. There is a plain-text twin, the
      `should_notify` filters are still pinned, and a source test of
      `agents/listener.py` finds `notify.on_message(cname, writer, m,
      ME_NAME)` once and neither `notify.push(`, `notify.should_notify(` nor
      the stale comment name `notify.should_notify` (the source pin greps for
      both strings; the call form with `(` and the bare name in the comment).
      `on_message` builds the push in `try`/`except`, logs `[listener]
      notify: image tags unreadable (…)` and falls back to plain text; the
      malformed-tag cases of design.md give the plain-text body without
      raising.
      `orchestrator/test_push_chain.py` and `orchestrator/test_push_send.py`
      are unchanged and green, and `wc -l agents/listener.py` gives 199.
- [x] 2.4a `chat/imeta.py` (design.md, fourth FAIL, gap 7): stdlib-only,
      `from_tags(tags)` and `clean_content(content, tags)`, which **never
      raise** on malformed tags (they return `[]` and the unchanged content).
      `agents/notify.py`
      loads it by file path with `importlib.util.spec_from_file_location`,
      not through `sys.path`. Proof: `chat/test_imeta.py` driven by
      `chat/testdata/imeta-event.json` (the one fixture; no second copy) plus the malformed shapes
      (`["imeta"]`, non-string fields, tags that are not a list), and
      `agents/test_notify.py` using the same fixture through the helper.
      `agent-image-to-chat-read` reuses this helper; its proposal (4.1) says
      so.
### Run C: retention, docs, English text and line limit (tasks 2.4, 2.5, 2.6)
Run C builds on main with runs A and B merged. **done_when:**
`jobs/test_prune_media.py` passes, `bash -n jobs/prune-media.sh` and
`pin_check.py` are green, the three docs contain `--image`, the English-text
check of 2.6 holds, `python3 scripts/line_limit.py` is green over the whole
repo (every file of A, B and C within its budget, no new baseline entry), and
`verify.sh` is green.

- [x] 2.4 Retention: the `media-prune` service (profile `maintenance`, rclone
      1.71) in `deploy/docker-compose.yml`, `jobs/prune-media.sh`, and
      `jobs/systemd/ratatoskr-media-prune.{service,timer}`. Proof: `bash -n`
      on the script, `pin_check.py` green, and `jobs/test_prune_media.py` with
      a fake `ssh` covering a prune followed by a size under and over
      `MEDIA_MAX_BYTES` (rc 0 and rc 1, the reason printed).
- [x] 2.5 Docs, since CI fails on code without docs. Grep under `docs/` found
      these that describe this behaviour:
      `docs/how-to/send-an-image.md` (new: the command; PNG, JPEG or WebP; at
      most 20 MiB in, 5 MiB out and 2560 px per side, refused rather than
      resized, with the traps (Playwright `fullPage`, `deviceScaleFactor: 2`)
      and the fixes (clip or viewport ≤ 2560, `scale: "css"`, matplotlib
      `figsize × dpi` ≤ 2560); metadata stripped with the pixels untouched;
      what is stripped is accidental metadata, not data hidden on purpose;
      refused: animated PNG or WebP, a rotated EXIF orientation, and Adobe
      APP14, CMYK or RGB-coded JPEG ("re-save as PNG"); on exit 10, crop or
      send a text ping instead; the required
      caption, exit codes 9 and 10, the 30-day retention, the `🖼 caption`
      push, that the thread does not show the picture until
      `agent-image-to-chat-read` is built, and failures);
      `docs/how-to/ping-from-a-session.md` (`--image`);
      `docs/how-to/troubleshooting.md` (a "no image" section: the helper's
      reasons, exit codes 9 and 10, and the prune timer). Proof: the three
      files contain `--image`, and the exit condition above holds.

- [x] 2.6 English interface text. Every new or changed line of this change that
      prints text (stderr, log and failure messages in `orchestrator/ping.sh`,
      `orchestrator/image_prep.py` and `jobs/prune-media.sh`) is English. The
      size-alarm message in
      `prune-media.sh` keeps its meaning: over the limit of `MEDIA_MAX_BYTES`,
      busier than expected, not deliberate growth. Pre-existing Dutch text is
      left alone. Proof: `jobs/test_prune_media.py`,
      `orchestrator/test_image_prep.py` and `orchestrator/test_ping_image.py`
      assert the English reason text on stderr (exit 2, exit 10, exit 9, rc 1
      over the limit), and a review check of `git diff main` over the three
      scripts finds no Dutch string in the added lines.

## 3. Live (host session, after merge)
- [ ] 3.1 Gate 3: the stripped `dirty.png`, `dirty.jpg`,
      `dirty-lossless.webp` and `dirty-lossy-alpha.webp`, each through the real `ping.sh --image` to
      `#statistics`. Each send must return `accepted`, and `messages get` must
      show the `imeta` tag and the caption. Then delete the messages and
      record the result in design.md. This is the only proof that the real CLI
      takes `--content '<caption>' --file <path> --mention <npub>` together
      (**unproven until this gate**; the fallback is to drop `--mention` on
      the image branch) and that
      the relay accepts the helper's output. If the relay refuses something,
      apply the fixed fallback from design.md gate 3 (JPEG without the JFIF
      APP0; WebP `ALPH` refused, or WebP refused; `--mention` dropped on the
      image branch),
      with its test, in a follow-up PR.
- [ ] 3.2 Right after the merge, install the prune unit **files** with
      `python3 scripts/check_units.py --install`. This copies them and runs
      `daemon-reload`, and enables nothing. Proof: `bash verify.sh` on
      agent-lxc is green, including `units` and `timers` (a disabled timer
      is not in `list-timers --all`, measured 2026-11-26).
- [ ] 3.3 Once 1.2 records the filter as safe:
      `systemctl --user enable --now ratatoskr-media-prune.timer`, and one run
      with `systemctl --user start ratatoskr-media-prune.service`. Proof: the
      journal shows the prune and a size under `MEDIA_MAX_BYTES`, and
      `check_timers.py` is green (`Result=success`, exit 0).
- [ ] 3.4 Gate 4 on Mark's phone: a real `ping.sh --image` to a project
      channel. The notification reads `🖼 caption` and a tap opens the
      channel. Record the notification-image probe in design.md.
- [ ] 3.5 Update `docs/reference/roadmap.yml` if this changes what "done"
      means for the chat. Tell Mark that the thread does not show the picture
      until `agent-image-to-chat-read` is built. Archive this change.

## 4. Handover
- [ ] 4.1 Propose `agent-image-to-chat-read` from design.md, "Handed to
      `agent-image-to-chat-read`": Gate 0 first, with the exact `buzz media
      get` invocation and stdout flag; the `_send` headers extension with its
      two-sided test. Proof: the change exists on main and its design.md
      records Gate 0 before any task of its build, and it reuses
      `chat/imeta.py` (2.4a) and `chat/testdata/imeta-event.json` instead of a
      second parser.
