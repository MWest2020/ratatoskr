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
- **Copy code with one tap.** Text between backticks (`` `like this` ``) and
  fenced blocks (```` ``` ````, with or without a language such as `bash`)
  show as code with a **⧉** button. One tap puts exactly that text on the
  clipboard, without the backticks or the language word; the button shows
  **✓** for a moment. This is the quick way to take a token or a command out
  of a message.
- **Reply** with the **↩** next to the author and time. A long press on the
  bubble no longer starts a reply: that is the selection gesture now.

If the clipboard refuses (no permission, or an old browser), the code is
selected instead and a message says why. Copy it from the browser's menu.

## Why it did not work

Nothing in the CSS blocked selection. Since the reply feature (0.17.0) a long
press of 500 ms on a bubble started a reply and moved the focus to the input.
On Android that is the same gesture, with about the same timing, as selecting
text: the reply won, the focus jump dropped the selection, and the keyboard
came up. A second, smaller cause: every new message re-rendered the list and
wiped a selection that was still open. The list now waits while a selection
sits in it, and renders as soon as it is gone.

## Where it lives

| part | file |
|---|---|
| message body: text, code, copy buttons, keeping a selection across polls | `chat/app-copy.js` |
| bubble styles, `user-select: text` said out loud | `chat/app.css` |
| reply action (no long press) | `chat/app-reply.js` |

## How it is tested

- **Unit:** `chat/test_copy.py` checks that no stylesheet sets
  `user-select: none` except on the copy button, that no app script listens to
  `touchstart`, `contextmenu` or `selectstart`, and runs the code splitter in
  node.
- **Browser, no VM needed:**
  `NODE_PATH=~/e2e-tools/node_modules node chat/e2e/select-copy.js` runs the
  working copy on a Pixel 7 profile with `/api/*` stubbed. It selects a bubble,
  checks a poll keeps the selection, long-presses a bubble, taps both copy
  buttons with clipboard permission granted, and checks the fallback.
