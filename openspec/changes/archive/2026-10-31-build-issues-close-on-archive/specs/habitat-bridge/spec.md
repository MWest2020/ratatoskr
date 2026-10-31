## ADDED Requirements

### Requirement: Issues of an archived change close by themselves

On a periodic tick the listener SHALL, for each open issue titled `build: <change>` or `propose: <change>`, read `openspec/changes` and `openspec/changes/archive` on that issue's repository, and SHALL close the issue only when the change id is absent from `openspec/changes` and exactly one archive directory `YYYY-MM-DD-<id>` exists. The detection SHALL be stateless: it SHALL read main itself and keep no snapshot. Each close SHALL carry a comment with the archive path as pointer, posted before the close. Only repositories with an open build issue SHALL be polled, at most one pair of listing calls per repository per tick. A change that is absent from `openspec/changes` without an archive directory SHALL NOT be closed, only logged. On a `gh` error or rate limit the listener SHALL skip the tick for that repository and log the reason. Issues that are already closed SHALL NOT be touched. A close that fails SHALL be logged with its reason.

#### Scenario: A change is archived

- **WHEN** a change is archived and an open `build: <change>` and an open `propose: <change>` issue exist
- **THEN** both are commented with the archive path and closed

#### Scenario: A change is removed without archive

- **WHEN** a change is absent from `openspec/changes` and no archive directory exists for it
- **THEN** its issues stay open and the listener logs that the change left main without an archive

#### Scenario: A change is still on main

- **WHEN** the change is still in `openspec/changes`
- **THEN** its issues are left alone

#### Scenario: Nothing open is left alone

- **WHEN** the change has no open `build:` or `propose:` issue, or the closer runs a second time
- **THEN** no issue is closed and no comment is posted

#### Scenario: The listener restarts with empty state

- **WHEN** the listener starts with no stored state and a change is already archived on main
- **THEN** the next tick closes its open issues with the archive path

#### Scenario: gh fails or is rate limited

- **WHEN** reading the listing from main fails
- **THEN** nothing is closed for that repository, and the reason is logged

#### Scenario: A close fails

- **WHEN** `gh` refuses to close an issue
- **THEN** the listener logs which issue and why, and carries on with the others
