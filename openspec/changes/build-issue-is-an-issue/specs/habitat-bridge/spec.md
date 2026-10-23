## ADDED Requirements

### Requirement: A build issue is an issue

When `!build` carries an issue number, the listener SHALL check with `gh` that
the number is an open issue on the repository, not a pull request and not a
closed issue, before the build uses it. When it is not, the listener SHALL open
a fresh build issue, build on that one, and say in the channel that the given
number was not an open issue and which issue is used instead.

#### Scenario: The number is an open issue

- **WHEN** `!build <repo> <change> <number>` is given and `<number>` is an open
  issue on the repository
- **THEN** the build runs on that issue and no new issue is opened

#### Scenario: The number is a pull request

- **WHEN** `!build <repo> <change> <number>` is given and `<number>` is a pull
  request
- **THEN** a fresh build issue is opened, the build runs on it, and the channel
  says the number was not an open issue and names the new one

#### Scenario: The number is a closed issue

- **WHEN** `!build <repo> <change> <number>` is given and `<number>` is a closed
  issue
- **THEN** a fresh build issue is opened, the build runs on it, and the channel
  says so
