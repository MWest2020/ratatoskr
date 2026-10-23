## ADDED Requirements

### Requirement: Odin starts a build, and the listener decides whether it runs

The hub MAY end an answer with `!build <repo> <change>`. The listener SHALL run
habitat's chain (architect, builder, reviewer, security) only when four
conditions hold:

- the repository is on the factory's list of Mark's repositories;
- the OpenSpec change exists on that repository's main;
- the work has an issue;
- the daily build budget is not used up.

It SHALL record each role's verdict and branch as a comment on that issue. A
build that does not meet a condition SHALL NOT start, and the listener SHALL
say which condition failed.

#### Scenario: A build without an issue does not start

- **WHEN** odin writes `!build wordsworth some-change` for work that has no
  issue
- **THEN** no Job runs, and the room says the build needs an issue first

#### Scenario: Every verdict is on the issue

- **WHEN** the chain runs for an issue
- **THEN** the issue gets one comment per role with its verdict and branch

### Requirement: A build that passes the cage and CI is merged without Mark

When all four roles pass, the listener SHALL open a pull request from the
builder branch, merge it once every check passes, and close the issue with a
link to the merge. alma SHALL never be a deploy target.

#### Scenario: A red check stops the merge

- **WHEN** one check on the pull request fails
- **THEN** nothing is merged, and the issue says which check failed

### Requirement: Closing is Mark's

Odin MAY create roles and channels. Closing a role or channel, or changing an
existing role's mandate or tools, SHALL only happen after Mark answers the
proposal with `!yes`, from his current pubkey.

#### Scenario: Odin proposes to close a channel

- **WHEN** odin proposes to archive a channel
- **THEN** nothing is archived until Mark answers `!yes`

### Requirement: The hub consults other agents itself

The hub MAY put `!consult <agent>[,<agent>] <question>` on the first line of
its answer. The listener SHALL then give each named agent (at most two;
existing, not the hub, and allowed to speak in that channel) one turn in the
same channel. That turn gets Mark's message and the hub's question, and the
agent answers under its own name. A consulted agent's answer SHALL NOT be read
for `!consult`, so consulting never chains. An agent that is refused SHALL be
named in the channel with the reason.

Added on Mark's decision of 2026-10-23 ("ja, bouw !consult"). Until then odin
had to ask Mark to post its questions to other agents: a `!route`d message is
posted under odin's key, and the loop guard skips agent messages, so nobody
answered it.

#### Scenario: Odin asks architect and reviewer

- **WHEN** odin answers with `!consult architect,reviewer Is this an MVP?`
- **THEN** after odin's answer, architect and then reviewer answer in the same
  channel, each with Mark's message and odin's question

#### Scenario: No chains

- **WHEN** a consulted agent writes `!consult bouwer …` itself
- **THEN** bouwer gets no turn
