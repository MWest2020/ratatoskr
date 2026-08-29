# jobs — recurring events (geplande claude -p-posts naar kanalen)

Geplande "nieuws"-jobs: op een tijdschema draait `claude -p` (sub-first) over
context van de host en post een digest naar een kanaal. Reboot-vast via
systemd user-timers (linger).

## Onderdelen
- `jobs.yml` — per job: kanaal-id, post-identiteit (handle), prompt, optioneel
  `context_cmd` (shell op de host; stdout = context voor claude -p).
- `run-job.py <naam>` — draait één job (context → claude -p → post).
- `run-jobs.sh <naam>` — SOPS-wrapper: exporteert NSEC_<HANDLE> en draait de job.
- systemd (agent-lxc, user): `boomhuis-job@<naam>.service` (template) +
  per-job timer `boomhuis-<kort>.timer`.

## Live jobs
- **news_from_zettelkast** (ma 09:00) — digest uit de zettelkast (journal +
  funding-memo), post als orchestrator.
- **proposals** (ma 09:15) — open OpenSpec-proposals uit het ecosysteem.
- **technical_depth** (vr 16:00) — architect reflecteert op technische schuld.

## Nieuwe job toevoegen
1. Kanaal aanmaken (web-app of `buzz channels create`), post-identiteit als lid.
2. Entry in `jobs.yml` (channel/identity/prompt/context_cmd).
3. Timer: kopieer een `boomhuis-*.timer` met een nieuwe `OnCalendar` + `Unit=`.
4. `systemctl --user daemon-reload && systemctl --user enable --now boomhuis-<x>.timer`.

Handmatig draaien/testen: `bash jobs/run-jobs.sh <naam>`.
