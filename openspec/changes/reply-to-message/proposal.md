# Reply to a message

## Why

Mark, 2026-10-22: *"can I select an agents message and reply to it, like in
slack, or whatsapp? would be great."* And on 2026-10-23: *"both, schedule it
... just work on it until done."*

Today a message cannot point at the message it answers. In a channel where
several agents talk, Mark has to name an agent with @ to reach it, and in
`#werkplaats` with several open issues a follow-up attaches to whichever issue
the room touched last.

The relay already supports it. `buzz messages send --reply-to <event-id>` adds
`["e", <parent-id>, "", "reply"]` (NIP-10, with marker), measured on
2026-10-23 in `#r6-smoke-4692`. The app and the listener ignore that tag.

## What changes

- **App.**
  - Every message has a reply action: a ↩ button, or a long press on the
    bubble.
  - The compose bar then shows "replying to <author>: <first line>", which can
    be cancelled.
  - The message is sent as a thread reply.
  - A reply shows a compact quote of its parent above the bubble.
- **Server.**
  - `/api/send` takes an optional `reply_to` (64 hex) and passes it as
    `--reply-to`. Anything else is refused with a reason.
  - `/api/messages` returns `reply_to`, read from the `e` tag with the `reply`
    marker.
- **Listener.**
  - A human's reply to an agent's message addresses that agent, in the same
    way an @mention does, and within the same channel scope. An explicit
    @mention still wins.
  - In a shared room, a reply continues the issue of the message it replies to.

## Out of scope

- Thread view: a separate pane listing a thread.
- Replies from agents to humans as threads.
