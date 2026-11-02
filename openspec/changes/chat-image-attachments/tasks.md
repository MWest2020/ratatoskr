# Tasks

Queued behind the other open work (Mark, 2026-11-02); see the proposal.

## 1. Gates (before anything else)
- [ ] **buzz media.** Check whether the buzz CLI or relay accepts media.
      Proof: a recorded command or request and its output, written into
      design.md under Gates. If it fails, amend design.md first.
- [ ] **Vision through Read.** Run `claude -p` under `--permission-mode dontAsk`
      with `Read(<dir>/**)` on a PNG and ask what is in it, with the model
      configured for the agent. Proof: the model describes the image; the run is
      recorded in design.md. If it fails, amend design.md first.

## 2. Server
- [ ] `POST /api/upload` in `chat/`: session gate and token, 5 MiB, magic
      bytes, EXIF strip, content-hash storage. Proof: new `chat/test_upload.py`
      covers no token, wrong magic behind a right header, SVG, over size, and
      EXIF removed.

## 3. UI
- [ ] `chat/app-attach.js`: paste, attach button, 3 per message, visible
      errors, `<img>` never via innerHTML. Proof: `chat/e2e/attach.js`
      (paste, refused SVG, fourth image refused); `chat/e2e/xss.js` still
      passes.

## 4. Listener
- [ ] Fetch, re-validate, write to per-turn scratch, pass the path, clean up,
      report failures. Proof: new `agents/test_attachments.py` covers delivery,
      cleanup, missing file and bad type.

## 5. The seam
- [ ] One test that runs upload and listener delivery together on the same
      file. Proof: `agents/test_attachments_chain.py`, checked by breaking the
      reference format on one side and seeing it fail.

## 6. Docs (CI fails on code without docs)
- [ ] New `docs/how-to/attach-images.md`: how to paste or attach, limits,
      accepted types, error messages.
- [ ] `docs/how-to/ping-from-a-session.md`: the chat HTTP API list gains
      `/api/upload`.
- [ ] `docs/how-to/pwa-installeren.md`: mention paste and attach.
- [ ] `chat/e2e/README.md`: the new e2e and what it needs.
- [ ] `docs/reference/roadmap.yml` if finishing this changes what "done" means.
