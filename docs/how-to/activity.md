---
status: current
last_reviewed: 2026-10-24
---

# Which agent ran, on what

Mark, 2026-10-24: *"can we track also which agents used with models and
skills and tools? I prob need this for a linkedin post."*

`agents/activity.py` writes one JSONL line per run to
`~/.local/state/ratatoskr/activity.jsonl`:

| field | chat turn | propose session | habitat role |
|---|---|---|---|
| `agent` | the handle | `propose-session` | the role |
| `project` | the channel | the repository | the repository |
| `model` | the model with the most tokens | from the session's init | the role file's model (`default` when it names none) |
| `skills` / `skills_used` | declared / loaded with the Skill tool | loaded | (none) |
| `tools` | `{tool: calls}` from the stream | from the run file | (not reported: the worker returns only its verdict) |
| `cost`, `turns`, `billing` | ✓ | ✓ | ✓ |

- `python3 scripts/activity_backfill.py` fills the history once, from the habitat run
  reports (the model from the job log with the same run id), the propose run
  files, and the `#statistics` history (no tool counts; the relay keeps only
  a recent window).
- `python3 scripts/activity_report.py [--json out.json]` summarises it per agent,
  model, project, tool, skill and bill.
