# One room, several agents, nobody pointed at

## Why

Mark, 2026-10-22: *"endgoal is I need to be able to talk to a bunch of agents at
the same time, see what they are doing, without pointing fingers (prob a common
scenario)."*

Today the listener decides who answers a human message in a fixed order:

1. an @mention;
2. the agent that spoke last, in its own channel;
3. the channel's default agent.

Every agent lives in its own channel. So Mark either picks the agent himself,
which is the pointing, or talks to odin, which routes and then hands the
message on. Nothing answers an agent, which is a deliberate loop guard, so a
hand-off from architect to bouwer always passes through Mark.

The role contracts (`role-contracts`) now say per role what it takes and what
is not its own. That is exactly the information a room needs to decide who
picks up a message, without Mark naming anyone.

## What changes

- **The room.** A channel, working name `#werkplaats`, holds the contracted
  agents: architect, bouwer and reviewer in the pilot.
- **Triage instead of pointing.** A human message without an @mention goes to
  one triage call. The call reads the message and the "Takes" and "Not mine"
  lines of each member's contract, and names the owner or owners with a reason.
  The listener posts that as a visible claim line, for example
  `→ architect: a design question (Takes: …)`. Only the named owners answer.
  An @mention still wins, as it does today.
- **A hand-off that is visible.** An agent can end its answer with
  `!handoff <agent> <one line>`. The listener then gives that agent one turn in
  the same room, with the hand-off line as its input. Each human message gets
  at most three hops, so two agents cannot keep each other busy.
- **Seeing what they do.** Claim lines, the progress lines that already exist
  (`⋯ architect: Read …`), and one status line per running turn. Nothing new
  is hidden in a log.

## Out of scope

- Agents that act without a human message. The room stays reactive.
- Building from the room. `!dispatch` stays Mark's.
- Replacing odin. #general and the hub stay as they are; the room is a second
  way in.

## Open (see design.md)

These questions are for Mark before this goes to "apply".
