## ADDED Requirements

### Requirement: A merged build queues the next step of its sequence

When the PR of a build merges, the listener SHALL read `proposal.md` of the merged change on the repository's main and, when it names a next step in the same sequence with a `Next:` line, SHALL queue that step's build by itself, as the hub (so `builds_per_day` applies). Only `Next:` SHALL be followed; a `Depends on` line SHALL be read only as the eligibility check (every named parent is merged) and SHALL NOT cause anything to be queued. The proposal SHALL be read with the raw `Accept` header, and a failed read SHALL be distinguished from a proposal that names no next step. The chain SHALL fire at the merge, without waiting for the merged change's deploy. The queued build SHALL go through the same checks as a `!build`: the circuit breaker, `max_concurrent`, `builds_per_day`, and the rule that the change exists on main. A step that is already building or queued SHALL NOT be queued again. The channel the build came from SHALL say which step was queued, or why none was.

#### Scenario: The merged change names a next step

- **WHEN** the PR of `originals-ingest-readers` merges and its proposal has a `Next: originals-ingest-write` line
- **THEN** a build of `originals-ingest-write` is queued and the channel says so

#### Scenario: A gate is closed

- **WHEN** the next step is chained while `max_concurrent` chains are running or the breaker has tripped for it
- **THEN** it waits in the queue or is refused with the gate's reason, and is never started around the gate

#### Scenario: No next step is named

- **WHEN** the merged change's proposal has no `Next:` line
- **THEN** nothing is queued and the channel says no next step was named

#### Scenario: Depends on is not followed

- **WHEN** the merged change's proposal has only a `Depends on: <parent>` line
- **THEN** nothing is queued, and a merged parent is never queued again

#### Scenario: A parent is not merged

- **WHEN** the named next step has a `Depends on` parent that is not merged
- **THEN** nothing is queued and the channel says which parent is missing

#### Scenario: Odin asks for the same step

- **WHEN** the chain has queued the next step and odin then sends `!build` for it
- **THEN** the `!build` is refused as already building or queued, the step is built once, and the circuit breaker is not tripped

#### Scenario: The merged change is still deploying

- **WHEN** the merged change is still deploying at the merge
- **THEN** the next step is queued anyway and the channel line says it builds on a merged main that may not be running yet

#### Scenario: Already queued

- **WHEN** the named step is already building or queued
- **THEN** it is not queued a second time

#### Scenario: The proposal cannot be read

- **WHEN** `gh` fails to read the proposal, or its body cannot be decoded
- **THEN** nothing is queued, and the failure is logged with its reason and said in the channel as a failed read, not as "no next step named"

### Requirement: A step with a deploy precondition is built, never deployed

When a chained step's own proposal names a deploy precondition, the listener SHALL queue it for build only: its PR merges as usual, but the listener SHALL NOT start the deploy, and SHALL say in the channel and on the issue that the deploy waits for a person.

#### Scenario: Precondition named

- **WHEN** a chained step's proposal names a deploy precondition and its PR merges
- **THEN** no deploy is started and the channel and the issue say the deploy waits

#### Scenario: No precondition

- **WHEN** a chained step's proposal names no deploy precondition
- **THEN** it is deployed after its merge like any other build
