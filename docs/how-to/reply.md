---
status: current
last_reviewed: 2026-11-15
---

# Reply to a message

Since ratatoskr-chat **0.17.0** (2026-10-23).

In the app, every message has a **↩** next to its author and time. Tap it;
the bar above the input then shows
what you are answering (`↩ replying to architect: …`). ✕ cancels, and
switching channels cancels too. When you send, the message goes to the relay
as a thread reply (`["e", <parent-id>, "", "reply"]`). In the app it shows a
small quote of the message it answers.

Until 2026-11-15 a long press on the bubble started a reply too. That was the
gesture a phone uses to select text, so it went (issue #245, see
[copy from the chat](copy-from-chat.md)).

## What the agents do with it

- **A reply to an agent's message addresses that agent,** as an @mention
  would, so you do not need to type the @. An explicit @mention still wins, and
  the agent's channel scope still applies.
- **In `#werkplaats`, a reply continues the issue of the message you reply
  to.** It does not pick whichever issue the room touched last. With several
  issues open, a reply is how you say which one you mean.

## Where it lives

| part | file |
|---|---|
| reply action, compose bar, quote | `chat/app-reply.js` |
| send with `reply_to`, refused when not 64 hex | `chat/actions.py`, `chat/server.py` |
| `reply_to` on every message, from the tags | `chat/threads.py`, `chat/read_routes.py` |
| who a reply addresses | `agents/replies.py`, `agents/triggers.py`, `agents/room_flow.py` |

## How it is tested

- **Unit:** `chat/test_threads.py` covers the parent read from the tags, the
  send with `--reply-to`, and a malformed id refused. `agents/test_replies.py`
  covers the order against @mention, the scope, and the room's issue.
- **Browser, against the installation:**
  `NAAM=… WW=… node chat/e2e/reply.js` posts two messages in
  `#r6-smoke-4692` (not polled by the listener), so no agent is triggered.
  It checks the bar, the relay's `reply` tag and the quote.
