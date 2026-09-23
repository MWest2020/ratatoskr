# Tasks

## 1. Decide
- [x] **For Mark.** Which channels get a default agent, and which handle?
      `#general → odin`, and nothing else. Mark, 2026-09-21: *"Ik wil eigenlijk
      enkel met Odin spreken"*.

## 2. Build
- [x] `default_agent` in `channels.yml`, read by a separate
      `bootstrap.load_channel_defaults` — the shape everything depends on
      (`{name: id}`) stays what it is.
- [x] Third trigger, in a new pure `agents/triggers.py` rather than inline in
      the poll loop: the order IS the contract and it must be testable.
- [x] `bootstrap.check_channel_defaults` refuses to start on a default that
      cannot speak in its channel.

## 3. The rem
- [x] `agents/test_triggers.py`: mention beats follow-up, mention beats default,
      follow-up beats default — and the reason names which rule fired, so a log
      can tell a live conversation from a cold start.
- [x] Only the most recent agent counts, humans in between do not break a
      follow-up, and outside the window nothing triggers.
