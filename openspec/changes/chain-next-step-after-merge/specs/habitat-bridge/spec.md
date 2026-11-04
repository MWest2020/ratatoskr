## ADDED Requirements

### Requirement: A merged build queues the next step of its sequence

When the PR of a build merges, the listener SHALL read `proposal.md` of the merged change on the repository's main and, when it names a next step in the same sequence with a `Next:` or `Depends on` line, SHALL queue that step's build by itself, as the hub (so `builds_per_day` applies). The queued build SHALL go through the same checks as a `!build`: the circuit breaker, `max_concurrent`, `builds_per_day`, and the rule that the change exists on main. A step that is already building or queued SHALL NOT be queued again. The channel the build came from SHALL say which step was queued, or why none was.

#### Scenario: The merged change names a next step

- **WHEN** the PR of `originals-ingest-readers` merges and its proposal has a `Next: originals-ingest-write` line
- **THEN** a build of `originals-ingest-write` is queued and the channel says so

#### Scenario: A gate is closed

- **WHEN** the next step is chained while `max_concurrent` chains are running or the breaker has tripped for it
- **THEN** it waits in the queue or is refused with the gate's reason, and is never started around the gate

#### Scenario: No next step is named

- **WHEN** the merged change's proposal has no `Next:` or `Depends on` line
- **THEN** nothing is queued and the channel says no next step was named

#### Scenario: Already queued

- **WHEN** the named step is already building or queued
- **THEN** it is not queued a second time

#### Scenario: The proposal cannot be read

- **WHEN** `gh` fails to read the proposal
- **THEN** nothing is queued and the failure is logged and said in the channel

### Requirement: A step with a deploy precondition is built, never deployed

When a chained step's own proposal names a deploy precondition, the listener SHALL queue it for build only: its PR merges as usual, but the listener SHALL NOT start the deploy, and SHALL say in the channel and on the issue that the deploy waits for a person.

#### Scenario: Precondition named

- **WHEN** a chained step's proposal names a deploy precondition and its PR merges
- **THEN** no deploy is started and the channel and the issue say the deploy waits

#### Scenario: No precondition

- **WHEN** a chained step's proposal names no deploy precondition
- **THEN** it is deployed after its merge like any other build
