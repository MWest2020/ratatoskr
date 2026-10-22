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

## Questions for Mark

1. **The room.** A new `#werkplaats` with architect, bouwer and reviewer? Or
   turn an existing channel into it?
2. **Hand-off.** Should agents hand off to each other within the room (with
   the hop limit), or does every hand-off stay with you?
3. **Odin.** Is odin a member of the room, or does it stay only in #general?
4. **Triage.** Is haiku fine as the triage model, or should it be the same
   model as odin?
