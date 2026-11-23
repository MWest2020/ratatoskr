# The role contract reaches the model

## Why

Mark, 2026-10-22: *"the problem is the overlap, regular hub&spoke isn't working
superfine. and we can try contract only. yes, pilot it."*

Two mandates claimed the same work. Architect said "concrete work goes through
an OpenSpec change", and bouwer said "turn an idea into an OpenSpec-change-shaped
task". The handbook gets a `## Contract` section per role, borrowed from the
BMAD method's role contract and not from its document set. The pilot covers
architect, bouwer and reviewer (MWest2020/handbook, Mark merges). The section
has five fields: Takes, Produces, Done when, Hands off to, and Not mine.

A section in the handbook reaches the human reader and nobody else.
`fetch_def` takes the system prompt from the chat facet only. That was the
lesson of `route_clause` (2026-09-13), and it showed up again while this change
was being written:

- **No agent had a prompt.** Since the handbook's English translation
  (2026-09-22), the heading read `## Chat facet` instead of `## Chat-facet`.
  The parser knew only the hyphen, so every chat agent ran with an empty
  system prompt. On 2026-10-22 that was 8 of 8 agents at 0 characters.
  - Fixed in cc5c600: the parser accepts both forms, and an agent without a
    prompt is not spawned.
- **roodteam never had one.** Its prompt is in a code fence, not a blockquote,
  so it has run without a prompt since it was created. It is offline until its
  definition uses a blockquote, which the same handbook PR does.

## What changes

- **The parser moves out.** It becomes `agents/defparse.py`, a pure module
  next to `bootstrap.py` that keeps both files under the line limit.
- **The contract is appended.** `parse_def` appends the role's `## Contract`
  section to its system prompt, with one instruction line: answer only what
  the contract says you take, and for anything under "Not mine", name whose it
  is and stop.
- **No contract, no change.** A definition without a contract keeps its
  prompt exactly as it was.
- **A contract is no prompt.** A contract without a prompt does not count as a
  prompt; the agent still does not run.

## Out of scope

- **Who picks up a message without an @mention.** That is the `shared-room`
  change.
- **Contracts for the other roles.** They follow once the pilot has carried one
  real change through architect, bouwer and reviewer.
