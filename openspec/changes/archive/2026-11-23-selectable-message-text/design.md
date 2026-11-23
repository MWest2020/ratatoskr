## Context

`app-reply.js` started a reply on a 500 ms `touchstart` hold on the bubble,
then focused the composer. `refresh()` (4 s poll) re-renders `#msgs` with
`innerHTML=""` whenever the message count changes. Message text went in as a
single `textContent`.

## Choices

- **Drop the long press instead of tuning it.** A long press on text is the
  platform's selection gesture on Android and iOS. Any timer on the same
  gesture races the platform, and the focus jump that a reply needs kills the
  selection either way. ↩ is already on every message; it gets a larger touch
  target.
  - *Rejected: a longer timer (e.g. 900 ms).* That still races, and a selection
    held a bit longer would still start a reply.
  - *Rejected: start the reply but skip the focus when a selection exists.* At
    500 ms the selection often does not exist yet, and a reply bar that pops up
    while you select is still wrong.
  - *Rejected: swipe to reply.* It is a new gesture to discover. A horizontal
    swipe also fights scrolling a long code line. It is out of scope here and
    can be proposed on its own.
- **Code parts by a small splitter, not a Markdown library.** Only code is
  needed (tokens, commands). One regex in `codeParts()` handles fenced blocks
  (an optional language word is dropped), a one-line fence, ``double``
  backticks and single backticks. Every part goes in through `textContent`, so
  no markup path is added. An unclosed fence stays text. An empty fence gets
  no button, because there is nothing to copy.
  - *Rejected: a Markdown renderer.* It adds a dependency and an HTML path into
    a PWA whose localStorage holds the device token. It also renders much more
    than was asked.
- **The copy button sits outside the selectable text.** It has
  `user-select: none`, so a selection across a message copies no ⧉. A block's
  button sits on a wrapper, so it does not scroll away with a long line.
- **Copy fallback.** The clipboard API needs a secure context and permission.
  When it is refused, the code is selected and `execCommand('copy')` is tried.
  If that copies, the selection is cleared again, so it does not hold the list
  back. If it does not, the selection stays for the native menu, and a toast
  says why it failed.
- **Hold the list while selecting, with a limit and a sign.** `refresh()` asks
  `holdRender(msgs, cid)` before it shows or counts anything. While a selection
  is open in `#msgs`, the list waits and a pill counts what waits. A tap shows
  it and scrolls down. The end of the selection shows it in place. After 30 s
  it shows anyway, so a selection left open never freezes the chat. Nothing
  counts as seen while it waits: `lastCount` and `markSeen` move only in
  `takeMessages()`, which is also the release. The held list carries its
  channel id: `selectChannel` drops it, and a release for a channel that is no
  longer open does nothing.
  - *Rejected: hold without a limit.* That was the first version. A selection
    left after a copy froze the chat silently, and unread state moved for
    messages nobody saw.
  - *Rejected: re-render and restore the selection by offsets.* That breaks
    when a message shifts, and the native selection handles on Android do not
    survive a DOM swap.
- **Pill text in English.** It is interface text (ADR-0001).
