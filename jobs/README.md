# jobs — recurring jobs (geplande claude -p-posts naar kanalen)

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
- **technical_debt** (vr 16:00) — architect reflecteert op technische schuld.
- **zettelkast_dagelijks** (dagelijks 09:00) — wat is er vandaag met Marks
  gedeelde clips gebeurd, wat staat er nog open. Draait ná de capture-run van de
  zettelkast (`zettelkast-daily.timer`, 06:00). De context splitst afgehandeld
  van open: een clip waarvan de fetch-snapshot al gecaptured is, is klaar — ook
  al citeert geen enkele wiki-pagina het clipbestand zelf.
- **standup** (dagelijks 08:00) — open werk (PR's/OpenSpec) + blokkades (#escalatie/#review).
- **gedaan** (dagelijks 18:00) — wat is er vandaag af (commits + gemergede PR's).

## Nieuwe job toevoegen
1. Kanaal aanmaken (web-app of `buzz channels create`), post-identiteit als lid.
2. Entry in `jobs.yml` (channel/identity/prompt/context_cmd).
3. Timer + template: `jobs/systemd/` bevat de gecommitte timers + het
   `boomhuis-job@.service`-template; kopieer die naar `~/.config/systemd/user/`. Het template hoort gelijk te blijven
   aan de live host-unit (waar news/proposals/technical_debt op draaien); wijk je
   ervan af, werk beide bij.
4. `systemctl --user daemon-reload && systemctl --user enable --now boomhuis-<x>.timer`.

Handmatig draaien/testen: `bash jobs/run-jobs.sh <naam>`.
