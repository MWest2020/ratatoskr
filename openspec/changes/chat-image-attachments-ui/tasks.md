# Tasks

Part 2 of the split of `chat-image-attachments`. Built only after
`chat-image-attachments` and `agent-image-to-chat-read` are merged.

## 1. Composer
- [ ] `chat/app-attach.js`: paste handler on the input, attach button, one
      image per message (a second replaces the first with a note), client
      type and size checks, preview from a blob URL revoked on remove and on
      send, caption from the input (empty refused), upload with the session
      token, the server's reason shown with `textContent`, the image kept
      after a failure. Proof: `chat/e2e/attach.js` below.
- [ ] Registered in `chat/statics.py` `FILES`, `chat/sw.js` `SHELL` and
      `FRESH_ASSETS`, and `chat/index.html`; `CACHE` in `chat/sw.js` moves to
      the next free version with a note. Proof: `chat/test_server.py` (or the
      statics test) serves `/app-attach.js`; `bash verify.sh` green, including
      the line limit with `chat/app.js` unchanged.
- [ ] The chat image pin moves one minor version. Proof:
      `scripts/pin_check.py` green.

## 2. e2e
- [ ] `chat/e2e/attach.js` against the VM: paste a PNG with a caption and
      find one new message from mark with an image; attach an SVG and see the
      refusal; attach a 6 MiB file and see the size limit; paste a second
      image and see the first replaced with a note; an empty caption refused.
      Proof: the run's output.
- [ ] `chat/e2e/xss.js` and `chat/e2e/smoke.js` still pass. Proof: the runs.

## 3. Docs
- [ ] New `docs/how-to/attach-images.md`: how to paste or attach, one per
      message, the accepted types and limits, each error message and what to
      do about it (over 2560 px, a rotated photo).
- [ ] `docs/how-to/pwa-installeren.md`: mention paste and attach.
- [ ] `chat/e2e/README.md`: `attach.js` and what it needs.
