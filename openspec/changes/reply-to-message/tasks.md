# Tasks

## 1. Server
- [x] `chat/threads.py`: `reply_parent(tags)` (pure) and `valid_event_id`.
- [x] `actions.send(..., reply_to)` → `--reply-to`; `/api/send` passes it.
      Messages carry `reply_to`.
- [x] Tests: the argv with and without `reply_to`; a malformed id is refused;
      the parent is read from the tags.

## 2. App
- [x] `chat/app-reply.js`: the reply action, the compose bar, and the quote
      above a reply. `app.js` changes by one line.
- [x] `index.html`, `sw.js` precache, `app.css`.

## 3. Listener
- [x] `agents/replies.py`: the parent of a message in its channel's history;
      the agent it addresses.
- [x] `triggers.pick` order: mention, then reply, then follow-up, then default.
- [x] Room: a reply continues the parent's issue and addresses the parent's
      agent.
- [x] Tests, mutation-checked.

## 4. Release and proof
- [x] `bash verify.sh` green; tag `chat-v0.17.0`; pin it in
      `deploy/docker-compose.yml`; roll it out on the relay VM.
- [x] e2e: `after-deploy.sh` (api, connection and smoke), plus a reply in the
      browser that the relay shows with its `reply` tag. 2026-10-23 on 0.17.0:
      api 39/39, connection 7/7, smoke 12/12; `chat/e2e/reply.js` 6/6 in
      #r6-smoke-4692. The temporary account was deleted afterwards.
- [x] Live: a reply to an agent's message gets that agent's answer without an
      @. 2026-10-23 20:20, #general: a reply to architect's message, with no @,
      got `reply @architect` and architect answered, not odin (the channel's
      default).
