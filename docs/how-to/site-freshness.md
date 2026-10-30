---
status: current
last_reviewed: 2026-10-30
---

# Keeping westerweel.work's pages current

Mark, 2026-10-30: his projects page still said "Boomhuis" weeks after the
rename, and he asked for "a job / service that keeps it up to date". Once a
week `orchestrator/site_freshness.py` checks the site's standing pages
(`content/nl/*.md`, `content/en/*.md`; blog posts keep the name of their day)
against facts.

## What it checks

| Check | Against | Kind |
|---|---|---|
| Old names (Boomhuis, coordinator, …) outside a "formerly" mention | the site's `data/renames.yml` | mechanical |
| A repository link whose repository moved | `gh repo view` | mechanical |
| A repository link that no longer exists | `gh repo view` | narrative |
| "The repo is private" where every linked repository is public | `gh repo view --json visibility` | narrative |
| A current public project no page links | the projects with a `docs/reference/roadmap.yml` | narrative |
| A parked or archived project still linked | `parked:` in `data/renames.yml`, `isArchived` | narrative |
| An English project section that shares almost no words with its goal | `roadmap.yml` goal and repository description | narrative |

## What it does with them

- **Mechanical** fixes go into one open pull request on westerweel-work,
  branch `freshness/<date>`. The job updates that PR on later runs and never
  merges it.
- **Narrative** findings are text in Mark's voice: one open issue on
  westerweel-work, labelled `waiting-on-mark`, with the findings as
  suggestions and `Default: the page stays as it is`. The job closes it when
  a later run finds nothing.
- The findings are written to `~/.local/state/ratatoskr/site-freshness.json`;
  `status_digest.py` turns a recent run with findings into one `site-stale`
  impediment in Mark's daily mail.

The site's own smoke test (`scripts/test-site.sh`) reads the same
`data/renames.yml`, so a renamed name can't come back through a normal edit
either.

## Run it

```bash
python3 orchestrator/site_freshness.py --dry-run   # print the findings, touch nothing
python3 orchestrator/site_freshness.py             # PR, issue, state file
```

It works in its own clone, `~/.worktrees/westerweel-freshness`
(`SITE_FRESHNESS_DIR`), reset to `origin/main` on every run.

## The timer

```bash
cp orchestrator/systemd/ratatoskr-site-freshness.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ratatoskr-site-freshness.timer   # Mondays 06:17
```

A new old name goes into the site's `data/renames.yml` (both checks read it).
