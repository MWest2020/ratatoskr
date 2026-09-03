# Change: add-standup-jobs

## Why

Mark wil dagelijks zicht: 's ochtends wat er open staat en wáár we vastlopen,
's avonds wat er af is. Nu bestaat alleen een wekelijkse zettelkast-digest en de
maandagse proposals — geen dagelijkse operationele cadans. Alles landde daardoor
ad hoc in #general.

## What Changes

- Nieuw kanaal **#standup** (recurring-jobs-kanaal).
- Twee recurring jobs via het bestaande `jobs/`-mechanisme:
  - **standup** (dagelijks 08:00) — open werk (PR's, OpenSpec-changes) + blokkades.
  - **gedaan** (dagelijks 18:00) — wat is er vandaag af (commits + gemergede PR's).
- Twee systemd-timers, in de repo gecommit (auditable).

## Scope

- `channels.yml` (#standup), `jobs/jobs.yml` (2 jobs), `jobs/run-job.py` (gedeelde
  runner: LEESFOUT-context bij time-out i.p.v. crash — raakt alle jobs), `jobs/systemd/` (2 timers +
  het gedeelde `boomhuis-job@.service`-template, nu mee-gecommit), `jobs/README.md`
  + root `README.md`.
- Post-identiteit = **orchestrator** (eigenaar van #standup): geen add-member nodig
  (kanaal-lidmaatschap-wijziging wordt door de auto-mode-classifier geblokkeerd).

## Out of scope

- Retro-committen van de bestaande job-timers (news/proposals/techdepth blijven
  host-only; pre-existing).
- Andere identiteiten in #standup.

## Risks

- Best-effort (erft het jobs-mechanisme): een lege of gefaalde `claude -p` post
  niks en laat niets falen. Een te brede context_cmd wordt op 6000 tekens gekapt.
