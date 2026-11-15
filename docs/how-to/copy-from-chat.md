---
status: current
last_reviewed: 2026-11-15
---

# Select and copy text in the chat

Issue [#245](https://github.com/MWest2020/ratatoskr/issues/245). Mark,
2026-11-15: "ik kan niet copy pasten vanuit ratatoskr. de text is niet
selectable."

## What you can do

- **Select any message text.** On a phone, press and hold a word: the
  browser's own selection handles and copy menu appear, as on any web page.
- **Copy code with one tap.** Text between backticks (`` `like this` ``, or
  double backticks when the code holds a backtick itself) and fenced blocks
  (```` ``` ````, with or without a language such as `bash`) show as code
  with a **⧉** button. An empty block has no button. One tap puts exactly that text on the
  clipboard, without the backticks or the language word; the button shows
  **✓** for a moment. This is the quick way to take a token or a command out
  of a message.
- **Reply** with the **↩** next to the author and time. A long press on the
  bubble no longer starts a reply: that is the selection gesture now.

If the clipboard refuses (no permission, or an old browser), the app tries
the browser's older copy command on the selected code. When that works the
selection goes again; when it does not, the code stays selected and a message
says why, so you can copy it from the browser's menu.

## New messages while you select

While text is selected in the message list, new messages wait so the selection
is not wiped. A pill above the input says **"N new messages — tap to show"**.
They show when you tap the pill (it scrolls down), when the selection ends, or
after 30 seconds at the latest, so a selection left open never freezes the
chat. Waiting messages do not count as read until they are shown, and they only
ever show in the channel they came from.

## Why it did not work

Nothing in the CSS blocked selection. Since the reply feature (0.17.0) a long
press of 500 ms on a bubble started a reply and moved the focus to the input.
On Android that is the same gesture, with about the same timing, as selecting
text: the reply won, the focus jump dropped the selection, and the keyboard
came up. A second, smaller cause: every new message re-rendered the list and
wiped a selection that was still open (see above for what happens now).

The spec change, with the rejected alternatives, is the OpenSpec change
`selectable-message-text`.

## Where it lives

| part | file |
|---|---|
| message body: text, code, copy buttons; the hold and its pill | `chat/app-copy.js` |
| hold before anything counts as seen (`refresh` → `takeMessages`) | `chat/app.js` |
| bubble styles, `user-select: text` said out loud | `chat/app.css` |
| reply action (no long press) | `chat/app-reply.js` |

## How it is tested

- **Unit:** `chat/test_copy.py` checks that no stylesheet sets
  `user-select: none` except on the copy button, that no app script listens to
  `touchstart`, `contextmenu` or `selectstart` (in any form), that nothing is
  counted as seen before the hold, and runs the code splitter in node.
- **Browser, no VM needed:**
  `NODE_PATH=~/e2e-tools/node_modules node chat/e2e/select-copy.js` runs the
  working copy on a Pixel 7 profile with `/api/*` stubbed (about a minute). It
  selects a bubble, checks the pill, the unread state and the 30 s release
  while a poll waits, a held list across a channel switch, a long press, both
  copy buttons with clipboard permission granted, and both fallbacks.
