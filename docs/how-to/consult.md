---
status: current
last_reviewed: 2026-10-23
---

# Odin consults other agents

Mark talks to odin; odin brings in who it needs.

    !consult architect,reviewer Is one publication end to end an MVP?

on the **first** line of odin's answer (`agents/consult.py`).

- **Who answers, and where.** After odin's answer, each named agent gets one
  turn in the **same channel**, with Mark's message and odin's question, and
  answers under its own name. Mark sees who says what.
- **At most two.** They must exist, cannot be odin, and must be allowed to
  speak in that channel. Anyone refused is named in the channel with the
  reason.
- **No chains.** A consulted agent's answer is not read for `!consult`.
- **Then odin acts.** Once they have answered, odin gets one follow-up turn
  with their answers, to take the step it announced (an issue, `!propose`,
  `!build`) or to tell Mark what blocks it. That turn cannot consult again or
  start a session, so the exchange ends there. Before 2026-10-23 nothing woke
  odin after a consult, and its "then I open the issues" never happened.

## The consulted agents can read the code

A chat turn may only read inside the listener tree. So the listener keeps a
shallow clone of main for each repository in `agents/factory.yml`
`readable` under `.repos/<name>/` (gitignored; `agents/repo_read.py`),
refreshed at most every ten minutes, and every agent is told where they are.
Nothing about them is writable: chat agents have Write and Edit denied.
`readable` is its own list rather than `repos`, so a private repository is
never readable by accident. Before this, the reviewer judged the wordsworth
pilot plan with "LIMIT: I can't read wordsworth".

## Why `!route` was not enough

`!route` posts the forwarded text under odin's own key. The listener skips
agent messages (the loop guard: nothing answers an agent), so a routed
question reached the channel and nobody answered it. On 2026-10-23 odin
therefore had to ask Mark to post its questions to architect and reviewer by
hand. `!consult` is the road it was missing.

## The hub keeps going

Every hub turn also carries `prompts.KEEP_GOING`. When a step of a decided
assignment finishes (a merge, a deploy, a consult), odin takes the next step
in the same answer, and stops only for what only Mark can give. Mark,
2026-10-24: *"always... always keep working until done. You / odin should have
gone ahead."*
