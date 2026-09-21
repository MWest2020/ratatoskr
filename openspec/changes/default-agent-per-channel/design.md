# Design — default agent per channel

## The decision

`channels.yml` gets an optional `default_agent: <handle>` per channel. The
listener uses it as the **third** trigger, after mention and follow-up.

Why in `channels.yml` and not in the agent definition: this is a property of the
**channel** ("who speaks here when nobody is named"), not of the agent. Two
agents could each claim to be the default of the same channel from their own
definition, and then the tie is settled by dict order — a bug that only shows up
in production as "the wrong one answered".

The handbook definition stays the gate for *whether* an agent may speak in a
channel at all. The default only chooses among what is already permitted; a
`default_agent` naming an agent that is not scoped to that channel is a
**configuration error and must fail loudly at startup**, not be skipped
silently.

## Rejected alternatives

**A global default (a hub for everything).** Simplest to write, and wrong in the
two channels where it matters most: feeds like #statistics and #escalatie would
get an answer to every line. Opt-in costs one key per channel and removes that
whole class.

**Widening the follow-up window from 10 messages to, say, 100.** Looks like a
one-character fix. It makes an agent wake up on a conversation it left an hour
ago, and it still does not solve the cold start in an empty channel.

**A classifier deciding "is this meant for an agent?".** A second model call to
decide whether to make the first one. It doubles the cost of the cheap case, and
its failure mode is silence — which is indistinguishable from a broken listener.
That is the failure class this repo already pays for elsewhere.

## The test that must come with it

The listener's trigger logic is a seam: mention, follow-up, default. A unit test
per branch is not enough — the bug that will happen is two branches both
claiming a message, or a default firing where a mention should have won. The
test asserts the **order**: mention beats follow-up beats default, and an agent
message never triggers anything.
