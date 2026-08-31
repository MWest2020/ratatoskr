# run-notifications Specification

## Purpose
TBD - created by archiving change add-notifications. Update Purpose after archive.
## Requirements
### Requirement: Posten gebeurt uitsluitend buiten de kooi

Posten naar de relay SHALL uitsluitend gebeuren door processen buiten de
habitat-kooi (orchestrator/dispatch op de orchestrator-host); worker-Jobs
SHALL geen relay-egress, geen buzz-sleutels en geen buzz-tooling krijgen.

#### Scenario: Kooi-diff is leeg

- **WHEN** deze change volledig is toegepast
- **THEN** is de diff op habitats `cage/`, `worker/` en NetworkPolicies leeg

### Requirement: Run-lifecycle in #runs

Per dispatch SHALL de start (rol, change, repo, run-id) en het einde (verdict,
kosten, branch, link naar het run-rapport) gepost worden in `#runs`, in één
thread per run.

#### Scenario: Groene run

- **WHEN** een builder-run slaagt
- **THEN** bevat de thread het PASS-verdict, de branchnaam en de rapportlink

### Requirement: Best-effort — de relay blokkeert nooit een run

Notificeren SHALL best-effort zijn: een onbereikbare relay of falende post
SHALL een dispatch of run nooit vertragen, blokkeren of laten falen; een
gemiste notificatie SHALL zichtbaar zijn in het lokale log.

#### Scenario: Relay plat tijdens een run

- **WHEN** de relay onbereikbaar is terwijl een run eindigt
- **THEN** rondt de run normaal af (verdict via git/exit-code zoals altijd) en
  logt de orchestrator de gemiste post

### Requirement: Berichten zijn spiegel en bevatten geen geheimen

Berichten SHALL alleen metadata en links bevatten — nooit PAT's, sleutels,
diff-inhoud van privérepo's of andere geheimen — en SHALL nooit de
gezaghebbende bron zijn: bij tegenspraak wint git + audit-JSONL.

#### Scenario: Tegenspraak

- **WHEN** een bericht en het audit-spoor in git elkaar tegenspreken
- **THEN** geldt git en wordt het bericht gecorrigeerd, nooit andersom

