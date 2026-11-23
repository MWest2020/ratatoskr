## MODIFIED Requirements

### Requirement: Mark is de poortwachter van de brug

Mark SHALL set the limits within which a dispatch from a message may run:
which repositories, how many builds a day, how many at a time, and which
worker image. They are kept in `agents/factory.yml`, under git. Inside those
limits the hub MAY dispatch a habitat chain itself (`!build`), and the
listener, not the model, SHALL check every condition before `chain.sh` runs:

- the repository is on the list;
- the OpenSpec change exists on that repository's main;
- the budget and concurrency limits hold;
- the work has an issue.

Widening the limits stays Mark's: odin cannot change `factory.yml`. A dispatch
outside them SHALL NOT start, and the refusal SHALL be said in the channel.

Changed on Mark's decision of 2026-10-22: *"definitely odin may build itself.
My repos, whenever possible or when it makes sense, openspecced, consulted and
yes."* Until then every dispatch from a message needed his explicit
confirmation.

#### Scenario: Odin builds inside the limits

- **WHEN** odin writes `!build ratatoskr <change>` and the change is on main,
  the budget holds and no chain is running
- **THEN** the chain runs without a confirmation from Mark, and its first trace
  is an issue

#### Scenario: Verzoek in #bouw

- **WHEN** a message in `#bouw` or `#general` asks for a build run
- **THEN** odin starts it with `!build` when it falls inside the limits, or says
  why not; the dispatch proposal no longer waits for Mark's confirmation

#### Scenario: Outside the limits

- **WHEN** odin asks for a build on a repository that is not on the list
- **THEN** nothing runs and the channel says why

### Requirement: De brug wordt niet gebouwd vóór het amendement

There SHALL be no task input towards the cage other than what habitat's
`worker-execution` spec allows: environment variables and git. The amendment
that spec required is in place: `HABITAT_TASK_REF` reads a file from the
cloned repository, and that is git. `!build` passes only the repository and
the change name; the task itself is the OpenSpec change on main, in git. A
task text from the chat SHALL NOT reach the cage.

#### Scenario: Verleiding tot een sluiproute

- **WHEN** someone wants a task text from the chat to reach the cage directly
- **THEN** that is refused; the task goes into an OpenSpec change in git first,
  and the build reads it from there

#### Scenario: A build carries no chat text into the cage

- **WHEN** odin starts a build from a message
- **THEN** the Job receives the repository and the change name only, and the
  worker reads the task from git
