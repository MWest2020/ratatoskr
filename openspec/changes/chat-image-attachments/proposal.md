# Pasting and uploading images in the chat

## Why

Mark, 2026-11-02, after asking odin whether it could see a page: *"Kun je die
zien?"* It could not. Everything the chat sends is text, so a screenshot of an
error never reaches an agent. Mark asked: *"can you do a proposal for web view
and pasting /uploading images?"*

What the code does today (from the ratatoskr session of 2026-11-02):

- The write path is text only. `chat/server.py` caps a POST at 16 KiB,
  `chat/actions.py` sends through `buzz messages send --content -`, and the UI
  puts text in the DOM with `textContent`. `chat/` has no upload, paste handler
  or file input.
- Agents read text only. `agents/relay.py` returns message text, and
  `agents/providers.py` starts `claude -p` with the prompt on stdin under
  `--permission-mode dontAsk`.
- The relay already has a media store (`BUZZ_S3_BUCKET=buzz-media` in
  `deploy/docker-compose.yml`), but nothing in the repo shows whether the buzz
  CLI or relay can write to it.

## What changes

This is part 1 of the session proposal: images in the chat. Part 2 is listed
under "Out of scope".

- **Chat UI.** A paste handler and an attach button in a new
  `chat/app-attach.js` (`app.js` is at the line limit). PNG, JPEG and WebP
  only; SVG is refused. Images are shown as `<img>` from a blob or same-origin
  URL, never through `innerHTML`.
- **`POST /api/upload`.** Behind the same session gate and session token as
  `/api/send`. Limits: 5 MiB per image and 3 images per message. The type is
  decided by magic bytes, not by the browser's Content-Type. EXIF is stripped.
  The file is stored under its content hash.
- **The message carries a reference only.** The image does not go through the
  relay, the audit JSONL or the git mirror. The text path stays as it is.
- **Delivery.** The listener fetches the file, validates it again and writes it
  to a per-turn scratch directory. The agent gets the path in its prompt and
  reads the image with `Read(<dir>/**)`, the pattern `scoped()` already uses.
  The directory is removed after the turn.
- **Visible errors.** Over the size or count limit, a refused type or a failed
  fetch each say what went wrong. Nothing is cut off silently.
- **Tests on the seam** (upload route, listener delivery, the two together,
  and an e2e in `chat/e2e`), and docs.

## Gates

The first two tasks are verification gates, because the design rests on two
assumptions nobody has checked:

1. Does the buzz CLI or relay accept media?
2. Does `claude -p` under `dontAsk` give the model a real image through `Read`,
   and does the model of the agent support vision?

If either fails, the design is amended before anything else is built.

## Out of scope

- The research-session screenshot (web view for `research` sessions) is a
  separate, later change on `werksessies`.
- A live iframe in the chat is rejected.
- Chat agents do not get web access.
- Anything in the habitat cage: no relay egress, buzz keys or `.mcp.json` for
  workers.

## Scheduling

Mark, 2026-11-02: *"Implement the proposal after all the other work... there's
quite a bit open."* This change is therefore queued behind the other open work;
it is not to be built first.

## Open questions

- Which open changes count as "the other work" that must land first? Default:
  everything already under `openspec/changes/` that is not archived.
- Where on the chat host does the content-hash store live (own volume or a
  directory), and how long are files kept? Not decided.
- Is the reference a line in the message text (`[img sha256:…]`) or a tag? That
  depends on gate 1 and is not decided.
