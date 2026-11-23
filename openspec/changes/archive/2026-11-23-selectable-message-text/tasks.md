# Tasks

## 1. App
- [x] `chat/app-reply.js`: no long press; ↩ gets a larger touch target.
- [x] `chat/app-copy.js`: `codeParts`, `bubbleFor`, copy buttons with the
      fallback, and the hold (pill, 30 s, per channel).
- [x] `chat/app.js`: `refresh` holds before `takeMessages`, which alone moves
      `lastCount` and marks seen; `selectChannel` drops a held list.
- [x] `chat/app.css`: `user-select: text` on `.bubble`, code, copy button, pill.
- [x] `index.html`, `statics.py` allowlist, `sw.js` shell (cache v32).

## 2. Tests
- [x] `chat/test_copy.py`: no `user-select:none` except the copy button; no
      select-gesture handler in any form; nothing counted as seen before the
      hold; `codeParts` cases in node.
- [x] `chat/e2e/select-copy.js` (Pixel 7, `/api` stubbed, no VM), 25 checks.
      Mutation-checked: without the channel guard, and with seen marked before
      the hold, it fails.

## 3. Release and proof
- [x] Build and tag a new chat image, pin it in `deploy/docker-compose.yml`,
      and roll it out on the relay VM; `after-deploy.sh` green.
- [ ] On Mark's phone: long-press selects a token, ⧉ copies it.
- [ ] Archive this change (`openspec archive selectable-message-text`) once it
      is live, as with `reply-to-message`.
