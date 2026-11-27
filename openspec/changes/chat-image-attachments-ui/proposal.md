# Paste or attach an image in the chat

## Why

Part 2 of the split of `chat-image-attachments` (its proposal, "Split after
the architect FAIL (ratatoskr#223) and the gate results"). Part 1 gives the
chat a server route, `POST /api/upload`, that checks one image and sends it
through the relay. This part gives Mark a way to use it from the composer, on
the phone and on the desktop: paste a screenshot, or pick a file.

## What changes

- **`chat/app-attach.js`** (new; `chat/app.js` is at the 200-line limit and
  is not touched): a paste handler on the message input and an attach button
  in the composer. One image per message. PNG, JPEG and WebP only, checked by
  type before upload; SVG is refused in the client too. The text in the input
  becomes the caption; an empty caption is refused with a hint, as the server
  does.
- **A preview before sending,** as an `<img>` from a blob URL, with a remove
  button. Never through `innerHTML`.
- **Visible errors.** The server's refusal reason is shown as it comes back
  (size, type, dimension, metadata, relay); a network failure says the image
  was not sent. Nothing is dropped silently.
- **Registered in all four places** a new chat file needs: `chat/statics.py`
  `FILES`, `chat/sw.js` `SHELL` and `FRESH_ASSETS`, a `<script>` tag in
  `chat/index.html`; `CACHE` in `chat/sw.js` moves one version.
- **e2e** `chat/e2e/attach.js` and docs.

## Not here

- Showing an image in the thread after it is sent, on reload or on another
  device: `agent-image-to-chat-read` owns the read route, the `images` field
  of `/api/messages`, the render hook and `chat/app-image.js`. This change
  adds no rendering of sent messages.
- The listener: `chat-image-attachments-deliver`.

## Depends on

`chat-image-attachments`, `agent-image-to-chat-read`

## Open questions

- `agent-image-to-chat-read` does not exist yet (`agent-image-to-chat` task
  4.1 proposes it). Default: this change waits for it; building the composer
  without it would send images Mark cannot see in his own thread.
- `agent-image-to-chat-read` moves `CACHE` in `chat/sw.js` to `v33`. Whichever
  of the two is built second takes the next version. Default: this change
  takes the next free version at build time and says so in its tasks.
