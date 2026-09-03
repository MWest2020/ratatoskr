# Tasks: add-mention-add-agent-ux

- [x] 1.1 `/api/send`: geen geforceerde `--mention`; niet-lid-mention → `409
      {missing_agent, known, channel}`.
- [x] 1.2 `/api/channel/add-member` + `roster.pubkey_of`.
- [x] 1.3 Frontend: pop-up "toevoegen?" + auto-retry na toevoegen; onbekende naam → melding.
- [x] 1.4 MENTION_PUBKEY-workaround verwijderd.
- [x] 1.5 Live gesmoked: @lid → ok, @niet-lid → 409, add-member → ok, retry → ok, onbekend → 404.
