# Design: who picks up a message in a shared room

## The choice: one triage call that reads the contracts

**Recommended: a dedicated triage call in the listener.**

- **The call.** `claude -p` with haiku and no tools. Its input is the human
  message plus the "Takes" and "Not mine" lines of each room member. Its output
  is JSON: `{"owners": ["architect"], "reason": "…"}`, validated against the
  room's members. Anything else counts as a failed triage.
- **When triage fails, nobody answers silently.** The listener posts "nobody
  took this: <reason>" and Mark mentions someone. That is the failure the
  `vervolg` fix of 2026-09-23 was about, where nobody answering looked exactly
  like a stopped listener.
- **One owner by default.** Two owners only when the message holds two
  separate questions, and the claim line says which part goes to whom.

### Rejected alternatives

- **Every agent decides for itself whether it is "mine".** Rejected. It costs
  one turn per member per message, and the agents race each other: two of them
  answer, or none does. That is the overlap again, moved into the room.
- **Odin triages.** Rejected for the pilot. Odin is the hub with its own
  conversation and a sonnet turn, and a hub that triages tends to answer
  itself. Triage is a classification, not a conversation; a small model with
  no tools fits and is cheap. This can be revisited once the room works.
- **Keyword or rule-based routing.** Rejected. The contracts are prose, so
  rules would be a second copy of them that drifts.

## Hand-off between agents

The loop guard "nothing answers an agent" stays the rule. `!handoff` is the
one exception, and it is bounded by three conditions:

1. **The target must be in the room**, and the hand-off must appear in the
   source agent's contract under "Hands off to". The listener checks both
   against the definition, not the prompt.
2. **There is a hop limit** of three per human message. Once it is reached,
   the listener says so in the room.
3. **One turn per hand-off.** The receiving agent answers once; it does not
   continue on its own.

## Seeing what happens

The room gets three kinds of lines, all from the listener:

- a claim line;
- progress lines (these already exist);
- one closing line per turn, with its duration.

The work-overview board can show "running in #werkplaats: architect, 40 s". No
dashboard is needed beyond that.

## Decided

Mark, 2026-10-22: *"merge everything I just want to know when it works. I
want the agents to work via git issues, so ther'e a reliable backtrack of what
is being done."* He answered none of the four questions himself, so the
recommendations stand:

1. **The room** is a new private `#werkplaats` with architect, bouwer and
   reviewer, created by the owner with `orchestrator/create-room.py`.
2. **Hand-offs** between agents are allowed, bounded by the contract and by
   three hops.
3. **Odin** stays in #general and is not a room member.
4. **Triage** runs on haiku, without tools.

## The trail: every piece of work is a GitHub issue

This was added after the questions above. It is the reason the room exists,
not an extra.

- **New work opens an issue** in the repo triage picked, which must be one of
  the room's `repos`. The issue holds the human's message and the triage
  reason, with the labels `agent-work`, `room:<room>` and `agent:<owner>`.
- **Everything is recorded:** every human message and every agent answer is
  an issue comment. A hand-off is a comment plus a label move. `!done` closes
  the issue with its line.
- **The listener writes, never the model:** fixed `gh` argv lists, with
  bodies on stdin (`agents/issues.py`), the same pattern as the read shell.
- **Which issue a message belongs to is read from the room.** The listener
  appends `· repo#N` to every room line, so a restart loses nothing and
  nothing is kept in memory.
- **Fail-closed on the trail.** Without an issue no turn starts. A later
  comment that fails is said in the room.

Rejected: keeping the mapping from message to issue in a local file. It is a
second truth next to the room, and the room is already in order and readable.
