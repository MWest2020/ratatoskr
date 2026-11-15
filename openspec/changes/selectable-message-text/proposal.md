# Selectable message text

## Why

Mark, 2026-11-15 (issue #245): *"ik kan niet copy pasten vanuit ratatoskr. de
text is niet selectable. moeten we fixen"*. A token or command sent in the chat
cannot be copied on his Android phone.

Nothing in the CSS blocks selection. The cause is the reply feature
(`reply-to-message`, chat 0.17.0): a 500 ms long press on a bubble starts a
reply and moves the focus to the composer. On Android that is the
text-selection gesture, with about the same timing. The reply wins, and the
focus jump drops the selection. A second cause: every new message re-renders
the list and wipes a selection that is still open.

This change follows the code in the same PR (a bug fix on a live app), so the
spec says what the app does once it is rolled out.

## What changes

- **Reply by button only.** The long press on the bubble goes; ↩ stays and
  gets a larger touch target. This modifies `Reply to a message`.
- **Text is selectable.** Message bodies say `user-select: text` explicitly.
  No app script listens to `touchstart`, `contextmenu` or `selectstart`.
- **Copy buttons on code.** Single- and double-backtick spans and fenced
  blocks render as code. Every non-empty code part gets a ⧉ button: one tap
  copies through `navigator.clipboard`. When that is refused, the code is
  selected, `execCommand('copy')` gets a try, and a toast says why it failed.
- **A selection survives a poll, but never freezes the chat.** While a
  selection sits in the message list, new messages wait behind a pill
  ("N new messages — tap to show"). They show on a tap, when the selection
  ends, or after 30 s. A waiting list is not counted as seen, and it belongs
  to its channel.

## Out of scope

- Markdown beyond code: bold, links, lists.
- Another reply gesture (swipe, double tap).
