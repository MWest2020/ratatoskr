## ADDED Requirements

### Requirement: A merged build requests the next step of its sequence

When the PR of a build merges, the listener SHALL read the merged change's `proposal.md` on the repository's main and, when it has a `## Next` section naming a change, SHALL request that step's build through the same `!build` road, as the hub. The request SHALL be made only when every change named in the next step's `## Depends on` section is merged and the next step has no `## Deploy precondition` section. A parent SHALL count as merged when it is the change that just merged or when a PR titled `build: <parent>` is merged on that repository. Proposals SHALL be read with the raw `Accept` header, and a failed read SHALL be distinguished from a proposal that names no next step. The channel the build came from SHALL say which step was requested, or why none was.

#### Scenario: The merged change names a next step

- **WHEN** the PR of `originals-ingest-readers` merges and its proposal has a `## Next` section naming `originals-ingest-write`, whose parents are merged
- **THEN** a build of `originals-ingest-write` is requested through `!build` as the hub, and the channel says so

#### Scenario: No next step is named

- **WHEN** the merged change's proposal has no `## Next` section
- **THEN** nothing is requested and the channel says no next step was named

#### Scenario: A parent is not merged

- **WHEN** the named next step has a `## Depends on` parent with no merged `build: <parent>` PR
- **THEN** nothing is requested and the channel names the missing parent

#### Scenario: The next step has a deploy precondition

- **WHEN** the named next step's proposal has a `## Deploy precondition` section
- **THEN** nothing is requested and the channel says a person starts that step

#### Scenario: A gate is closed

- **WHEN** the next step is requested while `max_concurrent` chains are running or the breaker has tripped for it
- **THEN** it waits in the queue or is refused with the gate's reason, as any `!build` would be

#### Scenario: Odin asks for the same step

- **WHEN** the chain has requested the next step and odin then sends `!build` for it
- **THEN** that `!build` is refused as already building or queued, the step is built once, and the circuit breaker is not tripped

#### Scenario: The proposal cannot be read

- **WHEN** `gh` fails to read a proposal, or the body is JSON instead of the raw file
- **THEN** nothing is requested, and the failure is logged with its reason and said in the channel as a failed read, not as "no next step named"

#### Scenario: The next step is already archived

- **WHEN** the `## Next` section names a change that is archived on that repository
- **THEN** nothing is requested and the channel says the next step is already done

## MODIFIED Requirements

### Requirement: One road from the chat to the cage

There SHALL be exactly one way to start a habitat run: the `!build` marker, which the listener checks (`agents/build.py`). A chat message reaches it through the hub's answer or Mark's message; a merged build reaches it through the listener requesting the next step of its sequence, which hands the same `!build` line to the same check. No other script in the repository SHALL dispatch habitat.

#### Scenario: The old bridge is gone

- **WHEN** someone looks for a way to dispatch habitat from the chat
- **THEN** they find `!build` and its how-to, and no `orchestrator/bridge.py`

#### Scenario: A chained step takes the same road

- **WHEN** a merged build's next step is requested
- **THEN** it passes through the same `!build` check as a step requested in the chat, and no other dispatch path exists
