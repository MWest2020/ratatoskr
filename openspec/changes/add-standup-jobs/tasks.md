# Tasks: add-standup-jobs

- [x] 1.1 #standup-kanaal aangemaakt (bd75be15…) + in `channels.yml`.
- [x] 1.2 `jobs/jobs.yml`: jobs `standup` (08:00) + `gedaan` (18:00), post als orchestrator.
- [x] 1.3 `jobs/systemd/`: `boomhuis-standup.timer` + `boomhuis-gedaan.timer` (Persistent).
- [x] 1.4 Beide jobs live gesmoked via `run-jobs.sh standup`/`gedaan` (exact de
      unit-ExecStart; niet de timer-trigger zelf) — posten in #standup.
- [x] 1.5 #standup-beschrijving gezet via set-channel-descriptions.py; recurring-jobs + channel-topology spec-deltas.
- [ ] 1.6 Deploy (post-merge): timers naar `~/.config/systemd/user/` op agent-lxc,
      `systemctl --user daemon-reload && enable --now boomhuis-standup.timer boomhuis-gedaan.timer`.
