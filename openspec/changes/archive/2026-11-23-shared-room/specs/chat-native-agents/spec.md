## ADDED Requirements

### Requirement: In a shared room the role contracts decide who answers

In a channel marked as a shared room, a human message without an @mention SHALL
go to one triage step. The triage step reads the "Takes" and "Not mine" lines
of each room member's contract and names one or more owners with a reason. The
listener SHALL post the outcome as a visible claim line, and only the named
owners SHALL answer. When triage fails or names nobody, the listener SHALL say
so in the room instead of staying silent. An @mention SHALL take precedence
over triage.

#### Scenario: A design question goes to architect

- **WHEN** Mark writes a design question in the shared room without naming an
  agent
- **THEN** the room shows a claim line naming architect and the reason, and
  only architect answers

#### Scenario: Nobody takes it

- **WHEN** triage names no owner
- **THEN** the room shows "nobody took this" with the reason

### Requirement: A hand-off between agents is visible and bounded

An agent in a shared room MAY end its answer with `!handoff <agent> <line>`.
The listener SHALL give the target one turn only when two conditions hold: the
target is a room member, and the target appears in the source agent's contract
under "Hands off to". A human message SHALL cause at most three hand-offs.

#### Scenario: The hop limit holds

- **WHEN** a third hand-off has run for one human message and an agent writes
  a fourth
- **THEN** no turn starts, and the room says the limit was reached
