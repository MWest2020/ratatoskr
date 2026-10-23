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

## Why `!route` was not enough

`!route` posts the forwarded text under odin's own key. The listener skips
agent messages (the loop guard: nothing answers an agent), so a routed
question reached the channel and nobody answered it. On 2026-10-23 odin
therefore had to ask Mark to post its questions to architect and reviewer by
hand. `!consult` is the road it was missing.
