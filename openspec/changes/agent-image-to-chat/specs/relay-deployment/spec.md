## ADDED Requirements

### Requirement: Message images are kept 30 days

Image blobs in the relay's media store SHALL be deleted once they are older
than 30 days, by a daily scheduled job whose definition is in git. Its
container image SHALL be pinned like every other image. The job SHALL fail,
visibly to the timer checks, when the store is still above 2 GiB after
pruning. Deleting an image SHALL NOT delete or change the message that
referred to it.

#### Scenario: The daily prune

- **WHEN** the job runs and the store holds an image uploaded 31 days ago and
  one uploaded yesterday
- **THEN** the older one is gone, yesterday's remains, and both messages still
  show their text

#### Scenario: The store keeps growing

- **WHEN** the store is above 2 GiB after the prune
- **THEN** the job exits non-zero and states the size and the limit, so the
  failing timer is reported
