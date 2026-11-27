# Design: the composer half

## Decisions

### A new file, and no line in `chat/app.js`

`chat/app.js` is at exactly 200 lines (`scripts/line_limit.py`). The composer
is not part of the message list, so `app-attach.js` needs no rendering hook in
`app.js`: it finds the input and the composer by id after load, adds the
paste listener and the button, and sends through its own `fetch` to
`/api/upload` with the session token header that `app-auth.js` already
provides. The send button's existing text path is unchanged; with an image
attached, the send goes to the upload route instead, carrying the input's
text as the caption.

Rejected: a hook in `app.js`'s send function (a line `app.js` does not have
room for, and a second owner of the send path); extending `app-reply.js`
(the reply file has its own job and `decorateRow` already).

### One image per message

The server accepts one image per request and makes one message
(`chat-image-attachments`, design.md). The composer holds at most one: a
second paste replaces the first after a visible note, so a pasted image never
disappears without the user seeing it.

Rejected: up to three per message as the 2 Nov design had (three relay
messages, or a multi-file event nobody has measured).

### Preview from a blob, never `innerHTML`

The preview is `document.createElement("img")` with `src` set to
`URL.createObjectURL(file)`, revoked when the image is removed or sent. The
only `innerHTML` in the message path stays the template-only one in
`chat/app.js`. `chat/e2e/xss.js` must still pass.

### Client-side checks are a courtesy, the server decides

The client refuses SVG and anything not `image/png`, `image/jpeg` or
`image/webp` before upload, and anything over 5 MiB, so the user hears it
early. The server repeats every check by magic bytes; the client never
decides alone.

### Errors

The server's reason is shown verbatim in the composer's error line
(`textContent`). A network failure or a 5xx without a body says "image not
sent" with the status. The image stays in the composer after a failure, so a
retry needs no new paste.

## Rejected alternatives

- **Drag and drop as the only way in.** Does not exist on a phone.
- **Showing the sent image from the local blob.** Would show an image the
  relay may have refused or changed; the thread shows what the relay holds,
  through `agent-image-to-chat-read`.
