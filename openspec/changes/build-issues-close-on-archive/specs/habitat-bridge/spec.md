## ADDED Requirements

### Requirement: Issues of a finished change close by themselves

When a change is archived, or removed from `main` without being archived, the listener SHALL close every open issue on that repository titled `build: <change>` or `propose: <change>`. Each close SHALL carry a comment with a pointer: the archive path when the change was archived, or the PR that removed or superseded it. Issues that are already closed SHALL NOT be touched. A close that fails SHALL be logged with its reason.

#### Scenario: A change is archived

- **WHEN** a change is archived and an open `build: <change>` and an open `propose: <change>` issue exist
- **THEN** both are closed, each with a comment naming the archive path

#### Scenario: A change is removed or split

- **WHEN** a change is removed from `main` without being archived, by a PR
- **THEN** its open `build:` and `propose:` issues are closed, each with a comment naming that PR

#### Scenario: Nothing open is left alone

- **WHEN** the change has no open `build:` or `propose:` issue, or the closer runs a second time
- **THEN** no issue is closed and no comment is posted

#### Scenario: A close fails

- **WHEN** `gh` refuses to close an issue
- **THEN** the listener logs which issue and why, and carries on with the others
