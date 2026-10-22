---
status: current
last_reviewed: 2026-10-22
---

# Work in the shared room (#werkplaats)

Talk to architect, bouwer and reviewer together without naming anyone.
Every piece of work becomes a GitHub issue, so what the agents did can be
traced later without reading the chat.

## What happens to a message

| you write | who answers | which issue |
|---|---|---|
| no @, nothing open | the agent whose contract covers it (triage) | a **new** issue |
| no @, right after an agent spoke | that agent (follow-up) | the issue the room was on |
| `@bouwer …` | bouwer | the current issue, or a new one |
| `… ratatoskr#12 …` | as above | issue 12 |

The room shows each step as a line from the listener:

- `→ architect takes this (triage: Takes: …) · ratatoskr#57`
- the agent's answer, ending with `· ratatoskr#57`
- `↪ architect → bouwer: write the change · ratatoskr#57`, a hand-off. The
  label `agent:architect` becomes `agent:bouwer`.
- `✓ bouwer: change on branch room-x · ratatoskr#57`. The issue is closed.

The issue holds everything: your message, every answer and every hand-off.
Its labels are `agent-work`, `room:werkplaats` and `agent:<who has it now>`.

    gh issue list --repo MWest2020/ratatoskr --label room:werkplaats

## The limits

- **The trail comes first.** If no issue can be opened, no agent starts. The
  room says `not started: could not open an issue …`.
- **Hand-offs follow the contract.** An agent may only pass work to someone
  named under "Hands off to" in its handbook contract.
- **At most three hand-offs** per message of yours. After that the room says
  it is over to you.
- **Nobody takes it** ("what's for lunch?"). The room says so; name an agent
  with @ if you want an answer anyway.

## Setting up a room

Run this once, as the owner. Agents may not add channel members.

    python3 orchestrator/create-room.py --name werkplaats --members architect,bouwer,reviewer

Then put the printed id in `channels.yml` with a `room:` block and restart
the listener:

```yaml
  werkplaats:
    id: <printed id>
    room:
      members: [architect, bouwer, reviewer]
      repos: [ratatoskr, handbook, wordsworth, habitat]   # first one is the default
      max_hops: 3
```

Turns run one at a time. Two agents in one message answer after each other,
not at the same moment.
